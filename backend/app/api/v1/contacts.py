"""Contact API endpoints."""

from uuid import UUID

import structlog
from fastapi import APIRouter, File, Query, Request, UploadFile

from app.dependencies import AuthUser, TenantDbSession
from app.core.pagination import PaginatedResponse
from app.schemas.common import SuccessResponse
from app.schemas.contacts import (
    ContactBulkAction,
    ContactCreate,
    ContactImportResponse,
    ContactListItem,
    ContactResponse,
    ContactUpdate,
)
from app.services.actor import actor_from_request
from app.services.contact_service import ContactService

logger = structlog.get_logger()
router = APIRouter()


@router.get("", response_model=PaginatedResponse[ContactListItem])
async def list_contacts(
    db: TenantDbSession,
    user: AuthUser,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=200),
    status: str | None = Query(default=None, pattern=r"^(active|inactive|blocked)$"),
    source: str | None = Query(default=None),
    tag_id: list[UUID] | None = Query(default=None),
    assigned_to: UUID | None = Query(default=None),
    sort: str = Query(default="-created_at"),
):
    """List contacts with search, filtering, and pagination."""
    svc = ContactService(db, user.company_id)
    items, total = await svc.list_contacts(
        limit=limit,
        offset=offset,
        search=search,
        status=status,
        source=source,
        tag_ids=tag_id,
        assigned_to=assigned_to,
        sort=sort,
    )
    return PaginatedResponse.create(
        items=items, total=total, limit=limit, offset=offset
    )


@router.post("", response_model=ContactResponse, status_code=201)
async def create_contact(
    data: ContactCreate,
    request: Request,
    db: TenantDbSession,
    user: AuthUser,
):
    """Create a new contact."""
    svc = ContactService(db, user.company_id, actor=actor_from_request(user, request))
    contact = await svc.create_contact(data)
    await db.commit()
    return contact


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: UUID,
    db: TenantDbSession,
    user: AuthUser,
):
    """Get a single contact."""
    svc = ContactService(db, user.company_id)
    return await svc.get_contact(contact_id)


@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: UUID,
    data: ContactUpdate,
    request: Request,
    db: TenantDbSession,
    user: AuthUser,
):
    """Update a contact."""
    svc = ContactService(db, user.company_id, actor=actor_from_request(user, request))
    contact = await svc.update_contact(contact_id, data)
    await db.commit()
    return contact


@router.delete("/{contact_id}", response_model=SuccessResponse)
async def delete_contact(
    contact_id: UUID,
    request: Request,
    db: TenantDbSession,
    user: AuthUser,
):
    """Soft-delete a contact."""
    svc = ContactService(db, user.company_id, actor=actor_from_request(user, request))
    await svc.delete_contact(contact_id)
    await db.commit()
    return SuccessResponse(message="Contact deleted")


@router.post("/bulk", response_model=SuccessResponse)
async def bulk_action(
    data: ContactBulkAction,
    request: Request,
    db: TenantDbSession,
    user: AuthUser,
):
    """Execute a bulk action on contacts."""
    svc = ContactService(db, user.company_id, actor=actor_from_request(user, request))
    count = await svc.bulk_action(
        contact_ids=data.contact_ids,
        action=data.action,
        tag_id=data.tag_id,
        status=data.status,
        assigned_to_user_id=data.assigned_to_user_id,
    )
    await db.commit()
    return SuccessResponse(message=f"Action '{data.action}' applied to {count} contacts")


@router.post("/import", response_model=ContactImportResponse)
async def import_contacts(
    file: UploadFile = File(...),
    db: TenantDbSession = None,
    user: AuthUser = None,
):
    """Import contacts from a CSV file. Processing runs asynchronously."""
    if not file.filename or not file.filename.endswith(".csv"):
        from app.core.exceptions import ValidationError
        raise ValidationError("Only CSV files are accepted")

    contents = await file.read()

    from app.tasks.import_tasks import process_csv_import
    task = process_csv_import.delay(
        csv_data=contents.decode("utf-8"),
        company_id=str(user.company_id),
        user_id=str(user.user_id),
    )

    return ContactImportResponse(task_id=task.id)
