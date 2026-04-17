"""Shipping models - providers, shipments, and tracking events."""

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
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class ShippingProvider(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Configured shipping carrier for a company."""

    __tablename__ = "shipping_providers"

    carrier: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # aramex, dhl, fetchr, shipa
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Carrier credentials (encrypted in practice)
    api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    api_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    def __repr__(self) -> str:
        return f"<ShippingProvider {self.carrier}>"


class Shipment(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """A shipment linked to a contact/deal."""

    __tablename__ = "shipments"
    __table_args__ = (
        Index("ix_shipment_tracking", "tracking_number"),
        Index("ix_shipment_company_status", "company_id", "status"),
    )

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shipping_providers.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Linked entities
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    deal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Tracking
    tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    carrier: Mapped[str] = mapped_column(String(50), nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="created"
    )  # created, picked_up, in_transit, out_for_delivery, delivered, failed, returned

    # Addresses
    origin_address: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    destination_address: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    # Recipient
    recipient_name: Mapped[str] = mapped_column(String(200), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(20), nullable=False)

    # Package
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # COD
    is_cod: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    cod_amount: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0, server_default="0")
    cod_currency: Mapped[str] = mapped_column(String(3), default="KWD")

    # Dates
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_delivery: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # WhatsApp notification tracking
    last_notification_status: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Relationships
    provider = relationship("ShippingProvider", lazy="noload")
    tracking_events = relationship(
        "ShipmentTrackingEvent", back_populates="shipment", lazy="noload",
        cascade="all, delete-orphan", order_by="ShipmentTrackingEvent.event_time.desc()"
    )

    def __repr__(self) -> str:
        return f"<Shipment {self.tracking_number} {self.status}>"


class ShipmentTrackingEvent(Base, UUIDMixin, TimestampMixin):
    """Individual tracking event for a shipment."""

    __tablename__ = "shipment_tracking_events"

    shipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shipments.id", ondelete="CASCADE"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Raw carrier data
    raw_data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    # Relationships
    shipment = relationship("Shipment", back_populates="tracking_events")

    def __repr__(self) -> str:
        return f"<TrackingEvent {self.status}>"
