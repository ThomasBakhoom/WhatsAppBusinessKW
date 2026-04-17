"""Schemas for contacts, tags, and custom fields."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import CamelModel


# ── Tags ──────────────────────────────────────────────────────────────────────


class TagCreate(CamelModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")
    description: str | None = None


class TagUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    description: str | None = None


class TagResponse(CamelModel):
    id: UUID
    name: str
    color: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime


# ── Custom Fields ─────────────────────────────────────────────────────────────


class CustomFieldCreate(CamelModel):
    name: str = Field(..., min_length=1, max_length=100)
    label: str = Field(..., min_length=1, max_length=200)
    field_type: str = Field(default="text", pattern=r"^(text|number|date|select|boolean)$")
    options: dict | None = None
    is_required: bool = False
    sort_order: int = 0


class CustomFieldUpdate(CamelModel):
    label: str | None = Field(default=None, min_length=1, max_length=200)
    options: dict | None = None
    is_required: bool | None = None
    sort_order: int | None = None


class CustomFieldResponse(CamelModel):
    id: UUID
    name: str
    label: str
    field_type: str
    options: dict | None = None
    is_required: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


# ── Custom Field Values ───────────────────────────────────────────────────────


class CustomFieldValueInput(CamelModel):
    custom_field_id: UUID
    value: str | None = None


class CustomFieldValueResponse(CamelModel):
    custom_field_id: UUID
    field_name: str
    field_label: str
    field_type: str
    value: str | None = None


# ── Contacts ──────────────────────────────────────────────────────────────────


class ContactCreate(CamelModel):
    phone: str = Field(..., min_length=1, max_length=20)
    email: EmailStr | None = None
    first_name: str = Field(default="", max_length=100)
    last_name: str = Field(default="", max_length=100)
    notes: str | None = None
    source: str = Field(default="manual", pattern=r"^(manual|import|whatsapp|landing_page|api)$")
    status: str = Field(default="active", pattern=r"^(active|inactive|blocked)$")
    opt_in_whatsapp: bool = True
    tag_ids: list[UUID] = Field(default_factory=list)
    custom_fields: list[CustomFieldValueInput] = Field(default_factory=list)
    assigned_to_user_id: UUID | None = None


class ContactUpdate(CamelModel):
    phone: str | None = Field(default=None, min_length=1, max_length=20)
    email: EmailStr | None = None
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    status: str | None = Field(default=None, pattern=r"^(active|inactive|blocked)$")
    opt_in_whatsapp: bool | None = None
    tag_ids: list[UUID] | None = None
    custom_fields: list[CustomFieldValueInput] | None = None
    assigned_to_user_id: UUID | None = None


class ContactResponse(CamelModel):
    id: UUID
    phone: str
    email: str | None = None
    first_name: str
    last_name: str
    full_name: str
    avatar_url: str | None = None
    notes: str | None = None
    source: str
    status: str
    opt_in_whatsapp: bool
    lead_score: int
    last_contacted_at: datetime | None = None
    assigned_to_user_id: UUID | None = None
    tags: list[TagResponse] = Field(default_factory=list)
    custom_fields: list[CustomFieldValueResponse] = Field(default_factory=list)
    company_id: UUID
    created_at: datetime
    updated_at: datetime


class ContactListItem(CamelModel):
    """Lighter response for list views."""
    id: UUID
    phone: str
    email: str | None = None
    first_name: str
    last_name: str
    full_name: str
    status: str
    source: str
    lead_score: int
    opt_in_whatsapp: bool
    last_contacted_at: datetime | None = None
    assigned_to_user_id: UUID | None = None
    tags: list[TagResponse] = Field(default_factory=list)
    created_at: datetime


class ContactBulkAction(CamelModel):
    contact_ids: list[UUID] = Field(..., min_length=1, max_length=500)
    action: str = Field(..., pattern=r"^(delete|add_tag|remove_tag|change_status|assign)$")
    tag_id: UUID | None = None
    status: str | None = None
    assigned_to_user_id: UUID | None = None


class ContactImportResponse(CamelModel):
    task_id: str
    message: str = "Import started"


class ContactImportResult(CamelModel):
    total: int
    created: int
    updated: int
    errors: int
    error_details: list[dict] = Field(default_factory=list)
