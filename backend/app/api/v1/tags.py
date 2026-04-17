"""Tag API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Request

from app.dependencies import AuthUser, TenantDbSession
from app.schemas.common import SuccessResponse
from app.schemas.contacts import TagCreate, TagResponse, TagUpdate
from app.services.actor import actor_from_request
from app.services.tag_service import TagService

router = APIRouter()


@router.get("", response_model=list[TagResponse])
async def list_tags(
    db: TenantDbSession,
    user: AuthUser,
):
    """List all tags for the company."""
    svc = TagService(db, user.company_id)
    return await svc.list_tags()


@router.post("", response_model=TagResponse, status_code=201)
async def create_tag(
    data: TagCreate,
    db: TenantDbSession,
    user: AuthUser,
    request: Request,
):
    """Create a new tag."""
    svc = TagService(db, user.company_id, actor=actor_from_request(user, request))
    tag = await svc.create_tag(data)
    await db.commit()
    return tag


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: UUID,
    db: TenantDbSession,
    user: AuthUser,
):
    """Get a single tag."""
    svc = TagService(db, user.company_id)
    return await svc.get_tag(tag_id)


@router.patch("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: UUID,
    data: TagUpdate,
    db: TenantDbSession,
    user: AuthUser,
    request: Request,
):
    """Update a tag."""
    svc = TagService(db, user.company_id, actor=actor_from_request(user, request))
    tag = await svc.update_tag(tag_id, data)
    await db.commit()
    return tag


@router.delete("/{tag_id}", response_model=SuccessResponse)
async def delete_tag(
    tag_id: UUID,
    db: TenantDbSession,
    user: AuthUser,
    request: Request,
):
    """Delete a tag."""
    svc = TagService(db, user.company_id, actor=actor_from_request(user, request))
    await svc.delete_tag(tag_id)
    await db.commit()
    return SuccessResponse(message="Tag deleted")
