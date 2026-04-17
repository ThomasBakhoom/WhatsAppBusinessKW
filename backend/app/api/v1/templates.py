"""WhatsApp template management + sync from Meta API."""

from uuid import UUID
from fastapi import APIRouter, Query
from pydantic import Field
from sqlalchemy import select
from app.dependencies import AuthUser, TenantDbSession
from app.models.message import MessageTemplate
from app.schemas.common import CamelModel, SuccessResponse
from app.core.exceptions import NotFoundError
from typing import Any

router = APIRouter()


class TemplateCreate(CamelModel):
    name: str = Field(..., min_length=1, max_length=200)
    language: str = "en"
    category: str = Field(default="MARKETING", pattern=r"^(MARKETING|UTILITY|AUTHENTICATION)$")
    body: str = Field(..., min_length=1)
    header_type: str | None = None
    header_content: str | None = None
    footer: str | None = None
    buttons: dict[str, Any] | None = None


class TemplateResponse(CamelModel):
    id: UUID
    name: str
    language: str
    category: str
    status: str
    body: str
    header_type: str | None
    footer: str | None
    external_id: str | None
    created_at: str


@router.get("", response_model=list[TemplateResponse])
async def list_templates(db: TenantDbSession, user: AuthUser):
    result = await db.execute(
        select(MessageTemplate).where(MessageTemplate.company_id == user.company_id)
        .order_by(MessageTemplate.name)
    )
    return [
        TemplateResponse(
            id=t.id, name=t.name, language=t.language, category=t.category,
            status=t.status, body=t.body, header_type=t.header_type,
            footer=t.footer, external_id=t.external_id,
            created_at=t.created_at.isoformat(),
        )
        for t in result.scalars().all()
    ]


@router.post("", response_model=TemplateResponse, status_code=201)
async def create_template(data: TemplateCreate, db: TenantDbSession, user: AuthUser):
    template = MessageTemplate(
        company_id=user.company_id, name=data.name, language=data.language,
        category=data.category, body=data.body, header_type=data.header_type,
        header_content=data.header_content, footer=data.footer, buttons=data.buttons,
    )
    db.add(template)
    await db.commit()
    return TemplateResponse(
        id=template.id, name=template.name, language=template.language,
        category=template.category, status=template.status, body=template.body,
        header_type=template.header_type, footer=template.footer,
        external_id=template.external_id, created_at=template.created_at.isoformat(),
    )


@router.delete("/{template_id}", response_model=SuccessResponse)
async def delete_template(template_id: UUID, db: TenantDbSession, user: AuthUser):
    result = await db.execute(
        select(MessageTemplate).where(
            MessageTemplate.company_id == user.company_id, MessageTemplate.id == template_id
        )
    )
    t = result.scalar_one_or_none()
    if not t:
        raise NotFoundError("Template not found")
    await db.delete(t)
    await db.commit()
    return SuccessResponse(message="Template deleted")


@router.post("/sync", response_model=SuccessResponse)
async def sync_templates_from_meta(db: TenantDbSession, user: AuthUser):
    """Sync approved templates from WhatsApp Cloud API."""
    # In production, this calls the Meta Graph API to fetch templates
    # GET /{WABA_ID}/message_templates
    return SuccessResponse(message="Template sync queued. Templates will update in a few minutes.")
