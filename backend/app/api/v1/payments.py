"""Payment, subscription, and billing API endpoints."""

import json
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, status

from app.config import get_settings
from app.dependencies import AuthUser, DbSession, TenantDbSession
from app.schemas.common import SuccessResponse
from app.schemas.payments import (
    CancelSubscriptionRequest,
    ChangePlanRequest,
    ChargeResponse,
    CreateChargeRequest,
    InvoiceResponse,
    PaymentResponse,
    PlanResponse,
    SubscriptionResponse,
)
from app.services.actor import actor_from_request
from app.services.subscription_service import SubscriptionService
from app.services.tap_payments import TapPaymentsService

logger = structlog.get_logger()
settings = get_settings()
router = APIRouter()


# ── Plans (public) ────────────────────────────────────────────────────────────

@router.get("/plans", response_model=list[PlanResponse])
async def list_plans(db: TenantDbSession, user: AuthUser):
    svc = SubscriptionService(db, user.company_id)
    return await svc.list_plans()


# ── Subscription ──────────────────────────────────────────────────────────────

@router.get("/subscription", response_model=SubscriptionResponse | None)
async def get_subscription(db: TenantDbSession, user: AuthUser):
    svc = SubscriptionService(db, user.company_id)
    return await svc.get_subscription()


@router.post("/subscription", response_model=SubscriptionResponse, status_code=201)
async def create_subscription(
    data: ChangePlanRequest, request: Request, db: TenantDbSession, user: AuthUser
):
    svc = SubscriptionService(db, user.company_id, actor=actor_from_request(user, request))
    sub = await svc.create_subscription(data.plan_id, data.billing_cycle)
    await db.commit()
    return sub


@router.post("/subscription/change", response_model=SubscriptionResponse)
async def change_plan(
    data: ChangePlanRequest, request: Request, db: TenantDbSession, user: AuthUser
):
    svc = SubscriptionService(db, user.company_id, actor=actor_from_request(user, request))
    sub = await svc.change_plan(data.plan_id, data.billing_cycle)
    await db.commit()
    return sub


@router.post("/subscription/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    data: CancelSubscriptionRequest, request: Request, db: TenantDbSession, user: AuthUser
):
    svc = SubscriptionService(db, user.company_id, actor=actor_from_request(user, request))
    sub = await svc.cancel_subscription(data.cancel_at_period_end)
    await db.commit()
    return sub


# ── Invoices ──────────────────────────────────────────────────────────────────

@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices(db: TenantDbSession, user: AuthUser):
    svc = SubscriptionService(db, user.company_id)
    return await svc.list_invoices()


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: UUID, db: TenantDbSession, user: AuthUser):
    svc = SubscriptionService(db, user.company_id)
    return await svc.get_invoice(invoice_id)


# ── Charges (Tap Payments) ────────────────────────────────────────────────────

@router.post("/charges", response_model=ChargeResponse)
async def create_charge(data: CreateChargeRequest, db: TenantDbSession, user: AuthUser):
    """Create a Tap Payments charge and return the payment redirect URL."""
    svc = SubscriptionService(db, user.company_id)
    invoice = await svc.get_invoice(data.invoice_id)

    tap = TapPaymentsService()
    result = await tap.create_charge(
        amount=invoice.total,
        currency=invoice.currency,
        payment_method=data.payment_method,
        description=f"Invoice {invoice.invoice_number}",
        reference_id=str(data.invoice_id),
        return_url=data.return_url,
    )
    await tap.close()

    # Record pending payment
    await svc.record_payment(
        invoice_id=data.invoice_id,
        amount=invoice.total,
        payment_method=data.payment_method,
        tap_charge_id=result["charge_id"],
        status="pending",
        gateway_response=result.get("gateway_response"),
    )
    await db.commit()

    return ChargeResponse(
        charge_id=result["charge_id"],
        payment_url=result["payment_url"],
        status=result["status"],
    )


# ── Payments ──────────────────────────────────────────────────────────────────

@router.get("/payments", response_model=list[PaymentResponse])
async def list_payments(db: TenantDbSession, user: AuthUser):
    svc = SubscriptionService(db, user.company_id)
    return await svc.list_payments()


# ── Tap Webhook ───────────────────────────────────────────────────────────────

@router.post("/tap-webhook")
async def tap_payment_webhook(request: Request, db: DbSession):
    """Handle Tap Payments webhook for payment confirmations.

    Verifies the HMAC-SHA256 signature in the `hashstring` header against the
    configured `TAP_WEBHOOK_SECRET`. Unsigned / mismatched requests are rejected
    with 401 so an attacker cannot fake a CAPTURED status.

    In development, if `TAP_WEBHOOK_SECRET` is empty the check is skipped so
    the mock flow keeps working; production refuses to start without the
    secret (enforced in config.py).
    """
    raw_body = await request.body()
    signature = (
        request.headers.get("hashstring")
        or request.headers.get("x-tap-signature")
        or request.headers.get("tap-signature")
    )

    if settings.tap_webhook_secret:
        if not TapPaymentsService.verify_webhook_signature(
            raw_body=raw_body,
            signature_header=signature,
            webhook_secret=settings.tap_webhook_secret,
        ):
            logger.warning("tap_webhook_rejected", reason="bad_signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )
    elif settings.is_production:  # pragma: no cover - config guard handles this
        logger.error("tap_webhook_rejected_prod_no_secret")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook verification is not configured",
        )

    try:
        payload = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        )
    logger.info("tap_webhook_received", charge_id=payload.get("id"))

    tap = TapPaymentsService()
    parsed = tap.parse_webhook(payload)

    charge_id = parsed["charge_id"]
    status_map = {
        "CAPTURED": "captured",
        "AUTHORIZED": "authorized",
        "FAILED": "failed",
        "DECLINED": "failed",
        "VOID": "refunded",
    }
    payment_status = status_map.get(parsed["status"], "pending")

    # Find payment by tap_charge_id
    from sqlalchemy import select
    from app.models.payment import Payment, Invoice

    result = await db.execute(
        select(Payment).where(Payment.tap_charge_id == charge_id)
    )
    payment = result.scalar_one_or_none()

    if payment:
        payment.status = payment_status
        payment.card_last_four = parsed.get("card_last_four")
        payment.card_brand = parsed.get("card_brand")
        payment.gateway_response = parsed.get("gateway_response", {})

        if payment_status == "failed":
            payment.failure_code = parsed["status"]
            payment.failure_message = f"Payment {parsed['status']}"

        # Update invoice
        if payment.invoice_id and payment_status == "captured":
            inv_result = await db.execute(
                select(Invoice).where(Invoice.id == payment.invoice_id)
            )
            inv = inv_result.scalar_one_or_none()
            if inv:
                from datetime import datetime, timezone
                inv.status = "paid"
                inv.paid_at = datetime.now(timezone.utc)

        await db.commit()
        logger.info("tap_payment_updated", charge_id=charge_id, status=payment_status)

    return {"status": "ok"}
