"""Custom field API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Request

from app.dependencies import AuthUser, TenantDbSession
from app.schemas.common import SuccessResponse
from app.schemas.contacts import CustomFieldCreate, CustomFieldResponse, CustomFieldUpdate
from app.services.actor import actor_from_request
from app.services.custom_field_service import CustomFieldService

router = APIRouter()


@router.get("", response_model=list[CustomFieldResponse])
async def list_custom_fields(
    db: TenantDbSession,
    user: AuthUser,
):
    """List all custom fields for the company."""
    svc = CustomFieldService(db, user.company_id)
    return await svc.list_fields()


@router.post("", response_model=CustomFieldResponse, status_code=201)
async def create_custom_field(
    data: CustomFieldCreate,
    db: TenantDbSession,
    user: AuthUser,
    request: Request,
):
    """Create a new custom field."""
    svc = CustomFieldService(db, user.company_id, actor=actor_from_request(user, request))
    field = await svc.create_field(data)
    await db.commit()
    return field


@router.patch("/{field_id}", response_model=CustomFieldResponse)
async def update_custom_field(
    field_id: UUID,
    data: CustomFieldUpdate,
    db: TenantDbSession,
    user: AuthUser,
    request: Request,
):
    """Update a custom field."""
    svc = CustomFieldService(db, user.company_id, actor=actor_from_request(user, request))
    field = await svc.update_field(field_id, data)
    await db.commit()
    return field


@router.delete("/{field_id}", response_model=SuccessResponse)
async def delete_custom_field(
    field_id: UUID,
    db: TenantDbSession,
    user: AuthUser,
    request: Request,
):
    """Delete a custom field."""
    svc = CustomFieldService(db, user.company_id, actor=actor_from_request(user, request))
    await svc.delete_field(field_id)
    await db.commit()
    return SuccessResponse(message="Custom field deleted")
