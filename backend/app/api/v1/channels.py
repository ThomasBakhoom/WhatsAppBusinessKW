"""Omnichannel API - manage messaging channels."""

from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import Field
from sqlalchemy import select
from app.dependencies import AuthUser, TenantDbSession
from app.models.channel import Channel, WebChatWidget
from app.models.company import Company
from app.schemas.common import CamelModel, SuccessResponse
from app.core.exceptions import NotFoundError
from app.services.actor import actor_from_request
from app.services.audit_service import AuditService
from app.utils.crypto import decrypt_value, encrypt_value
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

router = APIRouter()


# ── WhatsApp Cloud API connection ─────────────────────────────────────────────
# Config lives on the `companies` table (whatsapp_phone_number_id +
# whatsapp_business_account_id + whatsapp_api_token_encrypted) rather than
# the generic `channels` table, because the webhook + send paths already
# read from Company. This keeps a single source of truth.


class WhatsAppConfigResponse(CamelModel):
    connected: bool
    phone_number_id: str | None
    business_account_id: str | None
    has_token: bool  # never return the token itself


class WhatsAppConfigUpdate(CamelModel):
    phone_number_id: str = Field(..., min_length=1, max_length=50)
    business_account_id: str | None = Field(None, max_length=50)
    access_token: str = Field(..., min_length=10)  # Meta tokens are ~200 chars


class WhatsAppVerifyResponse(CamelModel):
    ok: bool
    phone_number_id: str
    display_phone_number: str | None = None
    verified_name: str | None = None
    quality_rating: str | None = None
    error: str | None = None


async def _load_company(db, company_id: UUID) -> Company:
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise NotFoundError("Company not found")
    return company


@router.get("/whatsapp", response_model=WhatsAppConfigResponse)
async def get_whatsapp_config(db: TenantDbSession, user: AuthUser):
    """Return the current WhatsApp connection status (token never exposed)."""
    company = await _load_company(db, user.company_id)
    return WhatsAppConfigResponse(
        connected=bool(company.whatsapp_phone_number_id and company.whatsapp_api_token_encrypted),
        phone_number_id=company.whatsapp_phone_number_id,
        business_account_id=company.whatsapp_business_account_id,
        has_token=bool(company.whatsapp_api_token_encrypted),
    )


@router.patch("/whatsapp", response_model=WhatsAppConfigResponse)
async def update_whatsapp_config(
    data: WhatsAppConfigUpdate,
    request: Request,
    db: TenantDbSession,
    user: AuthUser,
):
    """Save WhatsApp Cloud API credentials for the current company.

    The access token is encrypted with Fernet (AES-128-CBC) before storage
    so it's not visible as plaintext in the DB. The raw token is never
    returned in any response — use `/whatsapp/verify` to confirm it works.
    """
    company = await _load_company(db, user.company_id)
    old_phone = company.whatsapp_phone_number_id
    old_waba = company.whatsapp_business_account_id

    company.whatsapp_phone_number_id = data.phone_number_id.strip()
    if data.business_account_id is not None:
        company.whatsapp_business_account_id = data.business_account_id.strip() or None
    company.whatsapp_api_token_encrypted = encrypt_value(data.access_token.strip())

    # Audit the change — never log the raw token, just flag that it rotated.
    audit = AuditService(db, user.company_id, actor=actor_from_request(user, request))
    await audit.log(
        action="channel.whatsapp_connected",
        description=f"WhatsApp configured for {company.name}",
        resource_type="company",
        resource_id=str(company.id),
        changes={
            "phone_number_id": {"old": old_phone, "new": company.whatsapp_phone_number_id},
            "business_account_id": {"old": old_waba, "new": company.whatsapp_business_account_id},
            "token_rotated": True,
        },
    )

    await db.commit()
    return WhatsAppConfigResponse(
        connected=True,
        phone_number_id=company.whatsapp_phone_number_id,
        business_account_id=company.whatsapp_business_account_id,
        has_token=True,
    )


@router.delete("/whatsapp", response_model=SuccessResponse)
async def disconnect_whatsapp(
    request: Request,
    db: TenantDbSession,
    user: AuthUser,
):
    """Clear WhatsApp creds. Incoming messages to this number will be ignored."""
    company = await _load_company(db, user.company_id)
    if not company.whatsapp_phone_number_id:
        return SuccessResponse(message="Already disconnected")

    company.whatsapp_phone_number_id = None
    company.whatsapp_business_account_id = None
    company.whatsapp_api_token_encrypted = None

    audit = AuditService(db, user.company_id, actor=actor_from_request(user, request))
    await audit.log(
        action="channel.whatsapp_disconnected",
        description=f"WhatsApp disconnected for {company.name}",
        resource_type="company",
        resource_id=str(company.id),
    )

    await db.commit()
    return SuccessResponse(message="WhatsApp disconnected")


@router.post("/whatsapp/verify", response_model=WhatsAppVerifyResponse)
async def verify_whatsapp_connection(db: TenantDbSession, user: AuthUser):
    """Ping Meta's Graph API to confirm the stored credentials actually work.

    Calls GET https://graph.facebook.com/v19.0/{phone_number_id} which
    Meta responds to only if the token has permission for that number.
    """
    company = await _load_company(db, user.company_id)
    if not company.whatsapp_phone_number_id or not company.whatsapp_api_token_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="WhatsApp is not configured. Save credentials first.",
        )

    try:
        token = decrypt_value(company.whatsapp_api_token_encrypted)
    except Exception:
        return WhatsAppVerifyResponse(
            ok=False,
            phone_number_id=company.whatsapp_phone_number_id,
            error="Stored token is corrupted — re-save credentials.",
        )

    url = f"https://graph.facebook.com/v19.0/{company.whatsapp_phone_number_id}"
    params = {
        "fields": "display_phone_number,verified_name,quality_rating",
    }
    headers = {"Authorization": f"Bearer {token}"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, params=params, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("whatsapp_verify_network_error", error=str(exc))
        return WhatsAppVerifyResponse(
            ok=False,
            phone_number_id=company.whatsapp_phone_number_id,
            error=f"Network error reaching Meta: {exc}",
        )

    if r.status_code != 200:
        logger.warning(
            "whatsapp_verify_failed",
            status=r.status_code,
            body_prefix=r.text[:200],
        )
        return WhatsAppVerifyResponse(
            ok=False,
            phone_number_id=company.whatsapp_phone_number_id,
            error=f"Meta returned {r.status_code}. Check token permissions and phone number ID.",
        )

    body = r.json()
    return WhatsAppVerifyResponse(
        ok=True,
        phone_number_id=company.whatsapp_phone_number_id,
        display_phone_number=body.get("display_phone_number"),
        verified_name=body.get("verified_name"),
        quality_rating=body.get("quality_rating"),
    )



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
