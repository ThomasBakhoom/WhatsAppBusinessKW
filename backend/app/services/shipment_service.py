"""Shipment service - CRUD, tracking, WhatsApp notifications."""

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.shipping import Shipment, ShipmentTrackingEvent, ShippingProvider
from app.schemas.shipping import (
    ShipmentCreate,
    ShipmentListItem,
    ShipmentResponse,
    ShipmentUpdate,
    ShippingProviderCreate,
    ShippingProviderResponse,
    TrackingEventResponse,
)
from app.services.actor import Actor
from app.services.audit_service import AuditService
from app.services.shipping import get_carrier
from app.services.shipping.base import ShipmentRequest

logger = structlog.get_logger()


class ShipmentService:
    def __init__(self, db: AsyncSession, company_id: UUID, actor: Actor | None = None):
        self.db = db
        self.company_id = company_id
        self._audit = AuditService(db, company_id, actor=actor)

    # ── Providers ─────────────────────────────────────────────────────────────

    async def list_providers(self) -> list[ShippingProviderResponse]:
        result = await self.db.execute(
            select(ShippingProvider)
            .where(ShippingProvider.company_id == self.company_id)
            .order_by(ShippingProvider.is_default.desc(), ShippingProvider.display_name)
        )
        return [
            ShippingProviderResponse(
                id=p.id, carrier=p.carrier, display_name=p.display_name,
                is_active=p.is_active, is_default=p.is_default,
                account_number=p.account_number, created_at=p.created_at,
            )
            for p in result.scalars().all()
        ]

    async def create_provider(self, data: ShippingProviderCreate) -> ShippingProviderResponse:
        provider = ShippingProvider(
            company_id=self.company_id,
            carrier=data.carrier,
            display_name=data.display_name,
            is_default=data.is_default,
            api_key=data.api_key,
            api_secret=data.api_secret,
            account_number=data.account_number,
            config=data.config,
        )
        self.db.add(provider)
        await self.db.flush()

        await self._audit.log(
            action="shipment.provider_created",
            description=f"Shipping provider '{provider.display_name}' ({provider.carrier}) created",
            resource_type="shipping_provider",
            resource_id=str(provider.id),
            changes={
                "carrier": provider.carrier,
                "display_name": provider.display_name,
                "is_default": provider.is_default,
                "account_number": provider.account_number,
            },
        )

        return ShippingProviderResponse(
            id=provider.id, carrier=provider.carrier, display_name=provider.display_name,
            is_active=provider.is_active, is_default=provider.is_default,
            account_number=provider.account_number, created_at=provider.created_at,
        )

    # ── Shipments ─────────────────────────────────────────────────────────────

    async def list_shipments(
        self, *, status: str | None = None, limit: int = 20, offset: int = 0
    ) -> tuple[list[ShipmentListItem], int]:
        base = select(Shipment).where(Shipment.company_id == self.company_id)
        if status:
            base = base.where(Shipment.status == status)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        query = base.order_by(Shipment.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        items = [
            ShipmentListItem(
                id=s.id, carrier=s.carrier, tracking_number=s.tracking_number,
                status=s.status, recipient_name=s.recipient_name,
                recipient_phone=s.recipient_phone, is_cod=s.is_cod,
                cod_amount=s.cod_amount, created_at=s.created_at,
            )
            for s in result.scalars().all()
        ]
        return items, total

    async def get_shipment(self, shipment_id: UUID) -> ShipmentResponse:
        s = await self._get_or_404(shipment_id)
        return self._to_response(s)

    async def create_shipment(self, data: ShipmentCreate) -> ShipmentResponse:
        # Create shipment with carrier
        carrier_impl = get_carrier(data.carrier)
        carrier_result = await carrier_impl.create_shipment(ShipmentRequest(
            origin=data.origin_address.model_dump(),
            destination=data.destination_address.model_dump(),
            recipient_name=data.recipient_name,
            recipient_phone=data.recipient_phone,
            weight_kg=float(data.weight_kg) if data.weight_kg else None,
            description=data.description,
            is_cod=data.is_cod,
            cod_amount=float(data.cod_amount),
        ))

        shipment = Shipment(
            company_id=self.company_id,
            provider_id=data.provider_id,
            carrier=data.carrier,
            contact_id=data.contact_id,
            deal_id=data.deal_id,
            tracking_number=carrier_result.tracking_number,
            status="created",
            recipient_name=data.recipient_name,
            recipient_phone=data.recipient_phone,
            origin_address=data.origin_address.model_dump(),
            destination_address=data.destination_address.model_dump(),
            weight_kg=data.weight_kg,
            description=data.description,
            is_cod=data.is_cod,
            cod_amount=data.cod_amount,
            estimated_delivery=data.estimated_delivery,
        )
        self.db.add(shipment)
        await self.db.flush()

        # Add initial tracking event
        self.db.add(ShipmentTrackingEvent(
            shipment_id=shipment.id,
            status="created",
            description="Shipment created",
            location="Kuwait",
            event_time=datetime.now(timezone.utc),
        ))
        await self.db.flush()

        await self._audit.log(
            action="shipment.created",
            description=f"Shipment created for {shipment.recipient_name}",
            resource_type="shipment",
            resource_id=str(shipment.id),
            changes={
                "carrier": shipment.carrier,
                "tracking_number": shipment.tracking_number,
                "status": shipment.status,
                "recipient_name": shipment.recipient_name,
                "recipient_phone": shipment.recipient_phone,
                "is_cod": shipment.is_cod,
            },
        )

        return await self.get_shipment(shipment.id)

    async def update_shipment(self, shipment_id: UUID, data: ShipmentUpdate) -> ShipmentResponse:
        s = await self._get_or_404(shipment_id)
        old_status = s.status

        update_data = data.model_dump(exclude_unset=True)
        diff: dict = {}
        for key, value in update_data.items():
            old_value = getattr(s, key, None)
            if old_value != value:
                diff[key] = {"old": old_value, "new": value}
            setattr(s, key, value)

        # Track status change
        new_status = update_data.get("status")
        if new_status and new_status != old_status:
            self.db.add(ShipmentTrackingEvent(
                shipment_id=s.id,
                status=new_status,
                description=f"Status changed to {new_status}",
                event_time=datetime.now(timezone.utc),
            ))
            if new_status == "delivered":
                s.delivered_at = datetime.now(timezone.utc)

            # Trigger WhatsApp notification
            if s.contact_id and new_status != s.last_notification_status:
                s.last_notification_status = new_status
                from app.tasks.shipping_tasks import send_tracking_notification
                send_tracking_notification.delay(
                    company_id=str(self.company_id),
                    shipment_id=str(s.id),
                    contact_phone=s.recipient_phone,
                    status=new_status,
                    tracking_number=s.tracking_number or "",
                )

        await self.db.flush()

        if diff:
            action = "shipment.status_changed" if "status" in diff else "shipment.updated"
            await self._audit.log(
                action=action,
                description=f"Shipment {s.tracking_number or s.id} updated",
                resource_type="shipment",
                resource_id=str(s.id),
                changes=diff,
            )

        return await self.get_shipment(shipment_id)

    async def get_tracking(self, shipment_id: UUID) -> list[TrackingEventResponse]:
        result = await self.db.execute(
            select(ShipmentTrackingEvent)
            .where(ShipmentTrackingEvent.shipment_id == shipment_id)
            .order_by(ShipmentTrackingEvent.event_time.desc())
        )
        return [
            TrackingEventResponse(
                id=e.id, status=e.status, description=e.description,
                location=e.location, event_time=e.event_time,
            )
            for e in result.scalars().all()
        ]

    async def refresh_tracking(self, shipment_id: UUID) -> ShipmentResponse:
        """Poll carrier for latest tracking info."""
        s = await self._get_or_404(shipment_id)
        if not s.tracking_number:
            return self._to_response(s)

        carrier_impl = get_carrier(s.carrier)
        events = await carrier_impl.track_shipment(s.tracking_number)

        for event in events:
            existing = await self.db.execute(
                select(ShipmentTrackingEvent).where(
                    ShipmentTrackingEvent.shipment_id == s.id,
                    ShipmentTrackingEvent.status == event.status,
                    ShipmentTrackingEvent.description == event.description,
                )
            )
            if not existing.scalar_one_or_none():
                self.db.add(ShipmentTrackingEvent(
                    shipment_id=s.id,
                    status=event.status,
                    description=event.description,
                    location=event.location,
                    event_time=datetime.fromisoformat(event.event_time) if event.event_time else datetime.now(timezone.utc),
                    raw_data=event.raw_data or {},
                ))

        if events:
            latest = events[0]
            if latest.status != s.status:
                s.status = latest.status

        await self.db.flush()
        return await self.get_shipment(shipment_id)

    # ── Private ───────────────────────────────────────────────────────────────

    async def _get_or_404(self, shipment_id: UUID) -> Shipment:
        result = await self.db.execute(
            select(Shipment)
            .where(Shipment.company_id == self.company_id, Shipment.id == shipment_id)
            .options(selectinload(Shipment.tracking_events))
        )
        s = result.scalar_one_or_none()
        if not s:
            raise NotFoundError("Shipment not found")
        return s

    def _to_response(self, s: Shipment) -> ShipmentResponse:
        return ShipmentResponse(
            id=s.id, provider_id=s.provider_id, carrier=s.carrier,
            contact_id=s.contact_id, deal_id=s.deal_id,
            tracking_number=s.tracking_number, status=s.status,
            recipient_name=s.recipient_name, recipient_phone=s.recipient_phone,
            origin_address=s.origin_address, destination_address=s.destination_address,
            weight_kg=s.weight_kg, description=s.description,
            is_cod=s.is_cod, cod_amount=s.cod_amount, cod_currency=s.cod_currency,
            shipped_at=s.shipped_at, delivered_at=s.delivered_at,
            estimated_delivery=s.estimated_delivery,
            tracking_events=[
                TrackingEventResponse(
                    id=e.id, status=e.status, description=e.description,
                    location=e.location, event_time=e.event_time,
                )
                for e in (s.tracking_events or [])
            ],
            company_id=s.company_id,
            created_at=s.created_at, updated_at=s.updated_at,
        )
