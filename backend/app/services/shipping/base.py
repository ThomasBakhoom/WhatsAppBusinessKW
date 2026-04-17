"""Abstract shipping carrier interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass
class ShipmentRequest:
    origin: dict[str, str]
    destination: dict[str, str]
    recipient_name: str
    recipient_phone: str
    weight_kg: float | None = None
    description: str | None = None
    is_cod: bool = False
    cod_amount: float = 0
    reference: str = ""


@dataclass
class ShipmentResult:
    tracking_number: str
    carrier_reference: str
    label_url: str | None = None
    estimated_delivery: str | None = None
    raw_response: dict | None = None


@dataclass
class TrackingEvent:
    status: str
    description: str
    location: str | None = None
    event_time: str = ""
    raw_data: dict | None = None


class ShippingCarrier(ABC):
    """Abstract interface for shipping carriers."""

    @abstractmethod
    async def create_shipment(self, request: ShipmentRequest) -> ShipmentResult:
        """Create a shipment with the carrier. Returns tracking info."""
        ...

    @abstractmethod
    async def track_shipment(self, tracking_number: str) -> list[TrackingEvent]:
        """Get tracking events for a shipment."""
        ...

    @abstractmethod
    async def cancel_shipment(self, tracking_number: str) -> bool:
        """Cancel a shipment. Returns success status."""
        ...
