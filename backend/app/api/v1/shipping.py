"""Shipping API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.core.pagination import PaginatedResponse
from app.dependencies import AuthUser, TenantDbSession
from app.schemas.common import SuccessResponse
from app.schemas.shipping import (
    ShipmentCreate,
    ShipmentListItem,
    ShipmentResponse,
    ShipmentUpdate,
    ShippingProviderCreate,
    ShippingProviderResponse,
    TrackingEventResponse,
)
from app.services.actor import actor_from_request
from app.services.shipment_service import ShipmentService

router = APIRouter()


# ── Providers ─────────────────────────────────────────────────────────────────

@router.get("/providers", response_model=list[ShippingProviderResponse])
async def list_providers(db: TenantDbSession, user: AuthUser):
    svc = ShipmentService(db, user.company_id)
    return await svc.list_providers()


@router.post("/providers", response_model=ShippingProviderResponse, status_code=201)
async def create_provider(data: ShippingProviderCreate, db: TenantDbSession, user: AuthUser, request: Request):
    svc = ShipmentService(db, user.company_id, actor=actor_from_request(user, request))
    provider = await svc.create_provider(data)
    await db.commit()
    return provider


# ── Shipments ─────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[ShipmentListItem])
async def list_shipments(
    db: TenantDbSession,
    user: AuthUser,
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    svc = ShipmentService(db, user.company_id)
    items, total = await svc.list_shipments(status=status, limit=limit, offset=offset)
    return PaginatedResponse.create(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=ShipmentResponse, status_code=201)
async def create_shipment(data: ShipmentCreate, db: TenantDbSession, user: AuthUser, request: Request):
    svc = ShipmentService(db, user.company_id, actor=actor_from_request(user, request))
    shipment = await svc.create_shipment(data)
    await db.commit()
    return shipment


@router.get("/{shipment_id}", response_model=ShipmentResponse)
async def get_shipment(shipment_id: UUID, db: TenantDbSession, user: AuthUser):
    svc = ShipmentService(db, user.company_id)
    return await svc.get_shipment(shipment_id)


@router.patch("/{shipment_id}", response_model=ShipmentResponse)
async def update_shipment(shipment_id: UUID, data: ShipmentUpdate, db: TenantDbSession, user: AuthUser, request: Request):
    svc = ShipmentService(db, user.company_id, actor=actor_from_request(user, request))
    shipment = await svc.update_shipment(shipment_id, data)
    await db.commit()
    return shipment


@router.get("/{shipment_id}/tracking", response_model=list[TrackingEventResponse])
async def get_tracking(shipment_id: UUID, db: TenantDbSession, user: AuthUser):
    svc = ShipmentService(db, user.company_id)
    return await svc.get_tracking(shipment_id)


@router.post("/{shipment_id}/refresh", response_model=ShipmentResponse)
async def refresh_tracking(shipment_id: UUID, db: TenantDbSession, user: AuthUser, request: Request):
    """Poll carrier API for latest tracking info."""
    svc = ShipmentService(db, user.company_id, actor=actor_from_request(user, request))
    shipment = await svc.refresh_tracking(shipment_id)
    await db.commit()
    return shipment


# ── Carrier Webhook ───────────────────────────────────────────────────────────

@router.post("/webhook/{carrier}")
async def carrier_webhook(carrier: str, db: TenantDbSession, user: AuthUser):
    """Receive tracking webhooks from carriers."""
    # Carrier-specific webhook handling would go here
    return {"status": "ok"}
