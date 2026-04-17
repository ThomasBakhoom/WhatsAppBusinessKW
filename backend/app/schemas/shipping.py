"""Schemas for shipping."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import CamelModel


# ── Providers ─────────────────────────────────────────────────────────────────

class ShippingProviderCreate(CamelModel):
    carrier: str = Field(..., pattern=r"^(aramex|dhl|fetchr|shipa)$")
    display_name: str = Field(..., min_length=1, max_length=100)
    is_default: bool = False
    api_key: str | None = None
    api_secret: str | None = None
    account_number: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class ShippingProviderResponse(CamelModel):
    id: UUID
    carrier: str
    display_name: str
    is_active: bool
    is_default: bool
    account_number: str | None = None
    created_at: datetime


# ── Tracking Events ──────────────────────────────────────────────────────────

class TrackingEventResponse(CamelModel):
    id: UUID
    status: str
    description: str
    location: str | None = None
    event_time: datetime


# ── Shipments ─────────────────────────────────────────────────────────────────

class AddressInput(CamelModel):
    line1: str
    line2: str | None = None
    city: str
    state: str | None = None
    country: str = "KW"
    postal_code: str | None = None


class ShipmentCreate(CamelModel):
    provider_id: UUID | None = None
    carrier: str = Field(default="aramex", pattern=r"^(aramex|dhl|fetchr|shipa)$")
    contact_id: UUID | None = None
    deal_id: UUID | None = None
    recipient_name: str = Field(..., min_length=1, max_length=200)
    recipient_phone: str = Field(..., min_length=1, max_length=20)
    origin_address: AddressInput
    destination_address: AddressInput
    weight_kg: Decimal | None = None
    description: str | None = None
    is_cod: bool = False
    cod_amount: Decimal = Field(default=Decimal("0.000"))
    estimated_delivery: datetime | None = None


class ShipmentUpdate(CamelModel):
    status: str | None = Field(default=None, pattern=r"^(created|picked_up|in_transit|out_for_delivery|delivered|failed|returned)$")
    tracking_number: str | None = None
    shipped_at: datetime | None = None
    estimated_delivery: datetime | None = None


class ShipmentResponse(CamelModel):
    id: UUID
    provider_id: UUID | None = None
    carrier: str
    contact_id: UUID | None = None
    deal_id: UUID | None = None
    tracking_number: str | None = None
    status: str
    recipient_name: str
    recipient_phone: str
    origin_address: dict[str, Any]
    destination_address: dict[str, Any]
    weight_kg: Decimal | None = None
    description: str | None = None
    is_cod: bool
    cod_amount: Decimal
    cod_currency: str
    shipped_at: datetime | None = None
    delivered_at: datetime | None = None
    estimated_delivery: datetime | None = None
    tracking_events: list[TrackingEventResponse] = Field(default_factory=list)
    company_id: UUID
    created_at: datetime
    updated_at: datetime


class ShipmentListItem(CamelModel):
    id: UUID
    carrier: str
    tracking_number: str | None = None
    status: str
    recipient_name: str
    recipient_phone: str
    is_cod: bool
    cod_amount: Decimal
    created_at: datetime
