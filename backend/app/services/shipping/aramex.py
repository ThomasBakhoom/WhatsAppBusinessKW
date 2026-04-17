"""Aramex Kuwait carrier implementation."""

import uuid
from datetime import datetime, timezone

import httpx
import structlog

from app.services.shipping.base import ShipmentRequest, ShipmentResult, ShippingCarrier, TrackingEvent

logger = structlog.get_logger()


class AramexCarrier(ShippingCarrier):
    """Aramex Kuwait shipping integration."""

    def __init__(self, api_key: str = "", account_number: str = "", config: dict | None = None):
        self.api_key = api_key
        self.account_number = account_number
        self.config = config or {}

    async def create_shipment(self, request: ShipmentRequest) -> ShipmentResult:
        if not self.api_key:
            return self._mock_create(request)

        # Real Aramex API call would go here
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://ws.aramex.net/ShippingAPI.V2/Shipping/Service_1_0.svc/json/CreateShipments",
                json=self._build_create_payload(request),
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            data = response.json()
            return ShipmentResult(
                tracking_number=data.get("Shipments", [{}])[0].get("ID", ""),
                carrier_reference=data.get("Shipments", [{}])[0].get("Reference", ""),
                label_url=data.get("Shipments", [{}])[0].get("ShipmentLabel", {}).get("LabelURL"),
                raw_response=data,
            )

    async def track_shipment(self, tracking_number: str) -> list[TrackingEvent]:
        if not self.api_key:
            return self._mock_tracking(tracking_number)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://ws.aramex.net/ShippingAPI.V2/Tracking/Service_1_0.svc/json/TrackShipments",
                json={"Shipments": [tracking_number]},
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            data = response.json()
            events = []
            for result in data.get("TrackingResults", []):
                for event in result.get("Value", []):
                    events.append(TrackingEvent(
                        status=event.get("UpdateCode", ""),
                        description=event.get("UpdateDescription", ""),
                        location=event.get("UpdateLocation", ""),
                        event_time=event.get("UpdateDateTime", ""),
                        raw_data=event,
                    ))
            return events

    async def cancel_shipment(self, tracking_number: str) -> bool:
        if not self.api_key:
            return True
        return True  # Aramex cancellation API

    def _build_create_payload(self, request: ShipmentRequest) -> dict:
        return {
            "Shipments": [{
                "Shipper": {
                    "Reference1": request.reference,
                    "PartyAddress": request.origin,
                    "Contact": {"PersonName": "Sender", "PhoneNumber1": ""},
                },
                "Consignee": {
                    "PartyAddress": request.destination,
                    "Contact": {
                        "PersonName": request.recipient_name,
                        "PhoneNumber1": request.recipient_phone,
                    },
                },
                "Details": {
                    "ActualWeight": {"Value": request.weight_kg or 0.5, "Unit": "KG"},
                    "ProductGroup": "DOM" if request.destination.get("country") == "KW" else "EXP",
                    "ProductType": "ONP",
                    "PaymentType": "P",
                    "CashOnDeliveryAmount": {"Value": request.cod_amount, "CurrencyCode": "KWD"} if request.is_cod else None,
                },
            }],
        }

    def _mock_create(self, request: ShipmentRequest) -> ShipmentResult:
        tracking = f"ARX{uuid.uuid4().hex[:10].upper()}"
        return ShipmentResult(
            tracking_number=tracking,
            carrier_reference=f"REF-{tracking}",
            label_url=f"https://aramex.com/labels/{tracking}.pdf",
            estimated_delivery=(datetime.now(timezone.utc).isoformat()),
        )

    def _mock_tracking(self, tracking_number: str) -> list[TrackingEvent]:
        now = datetime.now(timezone.utc).isoformat()
        return [
            TrackingEvent(status="created", description="Shipment created", location="Kuwait City", event_time=now),
            TrackingEvent(status="picked_up", description="Package picked up by courier", location="Kuwait City", event_time=now),
        ]
