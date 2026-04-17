"""Schemas for payments, invoices, and subscriptions."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import CamelModel


# ── Plans ─────────────────────────────────────────────────────────────────────

class PlanResponse(CamelModel):
    id: UUID
    name: str
    display_name: str
    description: str | None = None
    price_monthly: Decimal
    price_yearly: Decimal
    currency: str
    max_contacts: int
    max_conversations_per_month: int
    max_team_members: int
    max_automations: int
    max_pipelines: int
    max_landing_pages: int
    has_ai_features: bool
    has_api_access: bool
    has_whatsapp_templates: bool
    sort_order: int


# ── Subscriptions ─────────────────────────────────────────────────────────────

class SubscriptionResponse(CamelModel):
    id: UUID
    plan_id: UUID
    plan: PlanResponse | None = None
    status: str
    billing_cycle: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    cancelled_at: datetime | None = None
    created_at: datetime


class ChangePlanRequest(CamelModel):
    plan_id: UUID
    billing_cycle: str = Field(default="monthly", pattern=r"^(monthly|yearly)$")


class CancelSubscriptionRequest(CamelModel):
    cancel_at_period_end: bool = True
    reason: str | None = None


# ── Invoices ──────────────────────────────────────────────────────────────────

class InvoiceResponse(CamelModel):
    id: UUID
    invoice_number: str
    status: str
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    currency: str
    period_start: datetime | None = None
    period_end: datetime | None = None
    paid_at: datetime | None = None
    line_items: list[dict[str, Any]]
    created_at: datetime


# ── Payments ──────────────────────────────────────────────────────────────────

class CreateChargeRequest(CamelModel):
    invoice_id: UUID
    payment_method: str = Field(default="knet", pattern=r"^(knet|visa|mastercard|apple_pay)$")
    return_url: str  # Redirect URL after payment


class ChargeResponse(CamelModel):
    charge_id: str
    payment_url: str  # Redirect customer here
    status: str


class PaymentResponse(CamelModel):
    id: UUID
    invoice_id: UUID | None = None
    amount: Decimal
    currency: str
    payment_method: str
    status: str
    tap_charge_id: str | None = None
    card_last_four: str | None = None
    card_brand: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    created_at: datetime
