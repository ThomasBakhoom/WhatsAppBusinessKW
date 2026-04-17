"""Subscription and billing service."""

import uuid as uuid_mod
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.models.payment import Invoice, Payment, Plan, Subscription
from app.schemas.payments import (
    InvoiceResponse,
    PaymentResponse,
    PlanResponse,
    SubscriptionResponse,
)
from app.services.actor import Actor
from app.services.audit_service import AuditService

logger = structlog.get_logger()


class SubscriptionService:
    def __init__(
        self,
        db: AsyncSession,
        company_id: UUID,
        actor: Actor | None = None,
    ):
        self.db = db
        self.company_id = company_id
        self.actor = actor
        self._audit = AuditService(db, company_id, actor=actor)

    # ── Plans ─────────────────────────────────────────────────────────────────

    async def list_plans(self) -> list[PlanResponse]:
        result = await self.db.execute(
            select(Plan).where(Plan.is_active == True).order_by(Plan.sort_order)
        )
        return [self._plan_response(p) for p in result.scalars().all()]

    async def get_plan(self, plan_id: UUID) -> PlanResponse:
        result = await self.db.execute(select(Plan).where(Plan.id == plan_id))
        plan = result.scalar_one_or_none()
        if not plan:
            raise NotFoundError("Plan not found")
        return self._plan_response(plan)

    # ── Subscription ──────────────────────────────────────────────────────────

    async def get_subscription(self) -> SubscriptionResponse | None:
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.company_id == self.company_id)
            .options(selectinload(Subscription.plan))
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return None
        return self._sub_response(sub)

    async def create_subscription(
        self, plan_id: UUID, billing_cycle: str = "monthly"
    ) -> SubscriptionResponse:
        """Create a new subscription (typically after registration)."""
        plan = await self.db.execute(select(Plan).where(Plan.id == plan_id))
        plan_obj = plan.scalar_one_or_none()
        if not plan_obj:
            raise NotFoundError("Plan not found")

        now = datetime.now(timezone.utc)
        if billing_cycle == "yearly":
            period_end = now + timedelta(days=365)
        else:
            period_end = now + timedelta(days=30)

        sub = Subscription(
            company_id=self.company_id,
            plan_id=plan_id,
            status="active",
            billing_cycle=billing_cycle,
            current_period_start=now,
            current_period_end=period_end,
        )
        self.db.add(sub)
        await self.db.flush()

        # Create initial invoice
        price = plan_obj.price_yearly if billing_cycle == "yearly" else plan_obj.price_monthly
        await self._create_invoice(sub.id, price, plan_obj.currency, now, period_end, plan_obj.display_name, billing_cycle)

        # Reload with plan
        result = await self.db.execute(
            select(Subscription).where(Subscription.id == sub.id).options(selectinload(Subscription.plan))
        )
        sub = result.scalar_one()
        await self._audit.log(
            action="subscription.created",
            description=f"Subscribed to plan '{plan_obj.display_name}' ({billing_cycle})",
            resource_type="subscription",
            resource_id=str(sub.id),
            changes={
                "plan_id": str(plan_id),
                "plan_name": plan_obj.display_name,
                "billing_cycle": billing_cycle,
                "status": sub.status,
                "current_period_end": sub.current_period_end.isoformat(),
            },
        )
        return self._sub_response(sub)

    async def change_plan(
        self, plan_id: UUID, billing_cycle: str = "monthly"
    ) -> SubscriptionResponse:
        """Change subscription plan."""
        sub_result = await self.db.execute(
            select(Subscription)
            .where(Subscription.company_id == self.company_id, Subscription.status.in_(["active", "trialing"]))
            .order_by(Subscription.created_at.desc()).limit(1)
        )
        sub = sub_result.scalar_one_or_none()
        if not sub:
            return await self.create_subscription(plan_id, billing_cycle)

        plan = await self.db.execute(select(Plan).where(Plan.id == plan_id))
        plan_obj = plan.scalar_one_or_none()
        if not plan_obj:
            raise NotFoundError("Plan not found")

        old_plan_id = sub.plan_id
        old_cycle = sub.billing_cycle
        sub.plan_id = plan_id
        sub.billing_cycle = billing_cycle
        now = datetime.now(timezone.utc)
        sub.current_period_start = now
        sub.current_period_end = now + (timedelta(days=365) if billing_cycle == "yearly" else timedelta(days=30))

        # Create invoice for new plan
        price = plan_obj.price_yearly if billing_cycle == "yearly" else plan_obj.price_monthly
        await self._create_invoice(sub.id, price, plan_obj.currency, sub.current_period_start, sub.current_period_end, plan_obj.display_name, billing_cycle)

        await self.db.flush()
        await self._audit.log(
            action="subscription.plan_changed",
            description=f"Plan changed to '{plan_obj.display_name}' ({billing_cycle})",
            resource_type="subscription",
            resource_id=str(sub.id),
            changes={
                "plan_id": {"old": str(old_plan_id), "new": str(plan_id)},
                "billing_cycle": {"old": old_cycle, "new": billing_cycle},
            },
        )
        result = await self.db.execute(
            select(Subscription).where(Subscription.id == sub.id).options(selectinload(Subscription.plan))
        )
        return self._sub_response(result.scalar_one())

    async def cancel_subscription(self, cancel_at_period_end: bool = True) -> SubscriptionResponse:
        sub_result = await self.db.execute(
            select(Subscription)
            .where(Subscription.company_id == self.company_id, Subscription.status == "active")
            .options(selectinload(Subscription.plan))
            .order_by(Subscription.created_at.desc()).limit(1)
        )
        sub = sub_result.scalar_one_or_none()
        if not sub:
            raise NotFoundError("No active subscription")

        old_status = sub.status
        if cancel_at_period_end:
            sub.cancel_at_period_end = True
            sub.cancelled_at = datetime.now(timezone.utc)
        else:
            sub.status = "cancelled"
            sub.cancelled_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self._audit.log(
            action="subscription.cancelled",
            description=(
                f"Subscription cancelled (at period end: {cancel_at_period_end})"
            ),
            resource_type="subscription",
            resource_id=str(sub.id),
            changes={
                "status": {"old": old_status, "new": sub.status},
                "cancel_at_period_end": {"old": False, "new": sub.cancel_at_period_end},
                "cancelled_at": sub.cancelled_at.isoformat(),
            },
        )
        return self._sub_response(sub)

    # ── Invoices ──────────────────────────────────────────────────────────────

    async def list_invoices(self, limit: int = 20) -> list[InvoiceResponse]:
        result = await self.db.execute(
            select(Invoice)
            .where(Invoice.company_id == self.company_id)
            .order_by(Invoice.created_at.desc())
            .limit(limit)
        )
        return [self._invoice_response(i) for i in result.scalars().all()]

    async def get_invoice(self, invoice_id: UUID) -> InvoiceResponse:
        result = await self.db.execute(
            select(Invoice).where(
                Invoice.company_id == self.company_id, Invoice.id == invoice_id
            )
        )
        inv = result.scalar_one_or_none()
        if not inv:
            raise NotFoundError("Invoice not found")
        return self._invoice_response(inv)

    # ── Payments ──────────────────────────────────────────────────────────────

    async def record_payment(
        self,
        invoice_id: UUID,
        amount: Decimal,
        payment_method: str,
        tap_charge_id: str,
        status: str = "captured",
        card_last_four: str | None = None,
        card_brand: str | None = None,
        gateway_response: dict | None = None,
    ) -> PaymentResponse:
        payment = Payment(
            company_id=self.company_id,
            invoice_id=invoice_id,
            amount=amount,
            currency="KWD",
            payment_method=payment_method,
            status=status,
            tap_charge_id=tap_charge_id,
            card_last_four=card_last_four,
            card_brand=card_brand,
            gateway_response=gateway_response or {},
        )
        self.db.add(payment)

        # Update invoice status
        inv_result = await self.db.execute(
            select(Invoice).where(Invoice.id == invoice_id)
        )
        inv = inv_result.scalar_one_or_none()
        if inv and status == "captured":
            inv.status = "paid"
            inv.paid_at = datetime.now(timezone.utc)

        await self.db.flush()
        return self._payment_response(payment)

    async def list_payments(self, limit: int = 20) -> list[PaymentResponse]:
        result = await self.db.execute(
            select(Payment)
            .where(Payment.company_id == self.company_id)
            .order_by(Payment.created_at.desc())
            .limit(limit)
        )
        return [self._payment_response(p) for p in result.scalars().all()]

    # ── Private ───────────────────────────────────────────────────────────────

    async def _create_invoice(
        self, subscription_id: UUID, amount: Decimal, currency: str,
        period_start: datetime, period_end: datetime, plan_name: str, cycle: str
    ) -> Invoice:
        # Generate invoice number
        count_result = await self.db.execute(
            select(func.count()).select_from(Invoice).where(
                Invoice.company_id == self.company_id
            )
        )
        count = count_result.scalar_one() + 1
        inv_number = f"INV-{datetime.now(timezone.utc).strftime('%Y%m')}-{count:04d}"

        inv = Invoice(
            company_id=self.company_id,
            subscription_id=subscription_id,
            invoice_number=inv_number,
            status="pending",
            subtotal=amount,
            tax_amount=Decimal("0.000"),
            total=amount,
            currency=currency,
            period_start=period_start,
            period_end=period_end,
            line_items=[{
                "description": f"{plan_name} - {cycle}",
                "quantity": 1,
                "unit_price": str(amount),
                "total": str(amount),
            }],
        )
        self.db.add(inv)
        await self.db.flush()
        return inv

    def _plan_response(self, p: Plan) -> PlanResponse:
        return PlanResponse(
            id=p.id, name=p.name, display_name=p.display_name,
            description=p.description,
            price_monthly=p.price_monthly, price_yearly=p.price_yearly,
            currency=p.currency,
            max_contacts=p.max_contacts,
            max_conversations_per_month=p.max_conversations_per_month,
            max_team_members=p.max_team_members,
            max_automations=p.max_automations,
            max_pipelines=p.max_pipelines,
            max_landing_pages=p.max_landing_pages,
            has_ai_features=p.has_ai_features,
            has_api_access=p.has_api_access,
            has_whatsapp_templates=p.has_whatsapp_templates,
            sort_order=p.sort_order,
        )

    def _sub_response(self, s: Subscription) -> SubscriptionResponse:
        return SubscriptionResponse(
            id=s.id, plan_id=s.plan_id,
            plan=self._plan_response(s.plan) if s.plan else None,
            status=s.status, billing_cycle=s.billing_cycle,
            current_period_start=s.current_period_start,
            current_period_end=s.current_period_end,
            cancel_at_period_end=s.cancel_at_period_end,
            cancelled_at=s.cancelled_at,
            created_at=s.created_at,
        )

    def _invoice_response(self, i: Invoice) -> InvoiceResponse:
        return InvoiceResponse(
            id=i.id, invoice_number=i.invoice_number, status=i.status,
            subtotal=i.subtotal, tax_amount=i.tax_amount, total=i.total,
            currency=i.currency,
            period_start=i.period_start, period_end=i.period_end,
            paid_at=i.paid_at, line_items=i.line_items,
            created_at=i.created_at,
        )

    def _payment_response(self, p: Payment) -> PaymentResponse:
        return PaymentResponse(
            id=p.id, invoice_id=p.invoice_id,
            amount=p.amount, currency=p.currency,
            payment_method=p.payment_method, status=p.status,
            tap_charge_id=p.tap_charge_id,
            card_last_four=p.card_last_four, card_brand=p.card_brand,
            failure_code=p.failure_code, failure_message=p.failure_message,
            created_at=p.created_at,
        )
