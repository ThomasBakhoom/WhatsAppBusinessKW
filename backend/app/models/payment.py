"""Payment, Invoice, and Subscription models."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class Plan(Base, UUIDMixin, TimestampMixin):
    """Subscription plans (global, not tenant-scoped)."""

    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Pricing (KWD)
    price_monthly: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    price_yearly: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KWD")

    # Feature limits
    max_contacts: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    max_conversations_per_month: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    max_team_members: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    max_automations: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    max_pipelines: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_landing_pages: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    has_ai_features: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    has_api_access: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    has_whatsapp_templates: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    def __repr__(self) -> str:
        return f"<Plan {self.name}>"


class Subscription(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Company subscription to a plan."""

    __tablename__ = "subscriptions"

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plans.id", ondelete="RESTRICT"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # active, past_due, cancelled, trialing

    billing_cycle: Mapped[str] = mapped_column(
        String(10), nullable=False, default="monthly"
    )  # monthly, yearly

    current_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    current_period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Tap Payments customer reference
    tap_customer_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Relationships
    plan = relationship("Plan", lazy="noload")

    def __repr__(self) -> str:
        return f"<Subscription {self.status}>"


class Invoice(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Invoice for a subscription period."""

    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("company_id", "invoice_number", name="uq_invoice_company_number"),
    )

    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Invoice details — unique per company (not globally).
    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )  # draft, pending, paid, failed, void

    # Amounts (KWD 3 decimals)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KWD")

    # Period
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Payment
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Line items
    line_items: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")

    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_number}>"


class Payment(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Individual payment transaction."""

    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payment_tap_charge", "tap_charge_id"),
    )

    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Amount
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KWD")

    # Payment method
    payment_method: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # knet, visa, mastercard, apple_pay

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, authorized, captured, failed, refunded

    # Tap Payments references
    tap_charge_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tap_payment_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Card info (masked)
    card_last_four: Mapped[str | None] = mapped_column(String(4), nullable=True)
    card_brand: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Error info
    failure_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Response data
    gateway_response: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    def __repr__(self) -> str:
        return f"<Payment {self.amount} {self.currency} {self.status}>"
