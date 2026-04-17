"""Omnichannel API - manage messaging channels."""

from uuid import UUID, uuid4
from fastapi import APIRouter, Request
from pydantic import Field
from sqlalchemy import select
from app.dependencies import AuthUser, TenantDbSession
from app.models.channel import Channel, WebChatWidget
from app.schemas.common import CamelModel, SuccessResponse
from app.core.exceptions import NotFoundError
from app.services.actor import actor_from_request
from app.services.audit_service import AuditService
from typing import Any

router = APIRouter()


class ChannelCreate(CamelModel):
    channel_type: str = Field(..., pattern=r"^(whatsapp|instagram|facebook_messenger|web_chat|sms|email)$")
    display_name: str = Field(..., min_length=1, max_length=100)
    credentials: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)


class ChannelResponse(CamelModel):
    id: UUID
    channel_type: str
    display_name: str
    is_active: bool
    is_default: bool
    config: dict[str, Any]
    created_at: str


class WebChatWidgetResponse(CamelModel):
    id: UUID
    name: str
    is_active: bool
    primary_color: str
    position: str
    welcome_message: str | None
    widget_token: str
    embed_code: str


@router.get("", response_model=list[ChannelResponse])
async def list_channels(db: TenantDbSession, user: AuthUser):
    result = await db.execute(
        select(Channel).where(Channel.company_id == user.company_id).order_by(Channel.channel_type)
    )
    return [
        ChannelResponse(
            id=c.id, channel_type=c.channel_type, display_name=c.display_name,
            is_active=c.is_active, is_default=c.is_default, config=c.config,
            created_at=c.created_at.isoformat(),
        )
        for c in result.scalars().all()
    ]


@router.post("", response_model=ChannelResponse, status_code=201)
async def create_channel(data: ChannelCreate, db: TenantDbSession, user: AuthUser, request: Request):
    channel = Channel(
        company_id=user.company_id, channel_type=data.channel_type,
        display_name=data.display_name, credentials=data.credentials, config=data.config,
    )
    db.add(channel)
    await db.flush()

    audit = AuditService(db, user.company_id, actor=actor_from_request(user, request))
    await audit.log(
        action="channel.created",
        description=f"Channel '{channel.display_name}' ({channel.channel_type}) created",
        resource_type="channel",
        resource_id=str(channel.id),
        changes={
            "channel_type": channel.channel_type,
            "display_name": channel.display_name,
            "credentials_set": bool(data.credentials),
        },
    )

    await db.commit()
    return ChannelResponse(
        id=channel.id, channel_type=channel.channel_type, display_name=channel.display_name,
        is_active=True, is_default=False, config=channel.config,
        created_at=channel.created_at.isoformat(),
    )


@router.delete("/{channel_id}", response_model=SuccessResponse)
async def delete_channel(channel_id: UUID, db: TenantDbSession, user: AuthUser, request: Request):
    result = await db.execute(
        select(Channel).where(Channel.company_id == user.company_id, Channel.id == channel_id)
    )
    ch = result.scalar_one_or_none()
    if not ch:
        raise NotFoundError("Channel not found")
    channel_name = ch.display_name
    channel_id_str = str(ch.id)
    await db.delete(ch)
    await db.flush()

    audit = AuditService(db, user.company_id, actor=actor_from_request(user, request))
    await audit.log(
        action="channel.deleted",
        description=f"Channel '{channel_name}' deleted",
        resource_type="channel",
        resource_id=channel_id_str,
        changes={"display_name": channel_name},
    )

    await db.commit()
    return SuccessResponse(message="Channel deleted")


# ── Web Chat Widget ───────────────────────────────────────────────────

@router.post("/web-chat-widget", response_model=WebChatWidgetResponse, status_code=201)
async def create_web_chat_widget(db: TenantDbSession, user: AuthUser, request: Request):
    """Create a web chat widget and get the embed code."""
    import secrets
    token = secrets.token_hex(32)
    widget = WebChatWidget(
        company_id=user.company_id, name="Web Chat",
        widget_token=token, welcome_message="Hi! How can we help you?",
        placeholder_text="Type a message...",
    )
    db.add(widget)
    await db.flush()

    audit = AuditService(db, user.company_id, actor=actor_from_request(user, request))
    await audit.log(
        action="channel.created",
        description=f"Web chat widget '{widget.name}' created",
        resource_type="web_chat_widget",
        resource_id=str(widget.id),
        changes={"name": widget.name, "position": widget.position},
    )

    await db.commit()

    from app.config import get_settings
    domain = get_settings().app_domain.rstrip("/")
    embed = f'<script src="{domain}/widget.js" data-token="{token}"></script>'
    return WebChatWidgetResponse(
        id=widget.id, name=widget.name, is_active=True,
        primary_color=widget.primary_color, position=widget.position,
        welcome_message=widget.welcome_message, widget_token=token,
        embed_code=embed,
    )
