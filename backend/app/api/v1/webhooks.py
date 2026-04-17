"""WhatsApp webhook endpoints for receiving messages and status updates."""

from datetime import datetime, timezone
from uuid import UUID

import structlog
from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import select

from app.config import get_settings
from app.core.database import AsyncSessionLocal, tenant_session
from app.models.company import Company
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.whatsapp.base import InboundMessage, StatusUpdate
from app.services.whatsapp.cloud_api import CloudAPIProvider
from app.websocket.manager import ws_manager

logger = structlog.get_logger()
settings = get_settings()

router = APIRouter()


@router.get("/whatsapp")
async def verify_whatsapp_webhook(
    mode: str = Query(alias="hub.mode", default=""),
    token: str = Query(alias="hub.verify_token", default=""),
    challenge: str = Query(alias="hub.challenge", default=""),
):
    """WhatsApp webhook verification (GET)."""
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("webhook_verified")
        return Response(content=challenge, media_type="text/plain")

    logger.warning("webhook_verification_failed", mode=mode)
    return Response(content="Forbidden", status_code=403)


def _iter_changes(payload: dict):
    """Yield (phone_number_id, change_value) for each WA Cloud API change."""
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {}) or {}
            phone_number_id = (value.get("metadata") or {}).get("phone_number_id")
            yield phone_number_id, value


async def _resolve_company_by_phone_number_id(
    phone_number_id: str,
) -> UUID | None:
    """Look up the company that owns this WhatsApp phone number.

    `companies` is NOT under RLS, so this query runs without tenant context.
    Returns the company UUID or None if no match (e.g. webhook for a number
    we don't recognize — likely a misconfigured forwarder).
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Company.id).where(
                Company.whatsapp_phone_number_id == phone_number_id
            )
        )
        return result.scalar_one_or_none()


@router.post("/whatsapp")
async def receive_whatsapp_webhook(request: Request):
    """Handle incoming WhatsApp Cloud API webhook events."""
    payload = await request.json()
    logger.info("webhook_received", payload_keys=list(payload.keys()))

    provider = CloudAPIProvider(
        access_token="",
        phone_number_id="",
        verify_token=settings.whatsapp_verify_token,
    )

    # Group events by phone_number_id so we can resolve the owning company
    # ONCE per change and process all that change's events under the right
    # tenant context. Without this, every RLS-protected query inside the
    # handlers would have no tenant set and fail.
    for phone_number_id, _value in _iter_changes(payload):
        if not phone_number_id:
            logger.warning("webhook_change_no_phone_number_id")
            continue

        company_id = await _resolve_company_by_phone_number_id(phone_number_id)
        if company_id is None:
            logger.warning(
                "webhook_no_company_for_phone_number_id",
                phone_number_id=phone_number_id,
            )
            continue

        # Re-parse the full payload to get InboundMessage / StatusUpdate
        # objects, then filter to events from THIS phone_number_id by walking
        # the same payload structure. (Cleaner than refactoring parse_webhook
        # to be change-aware.) We pass a single-change payload to the parser.
        single = {
            "entry": [
                {
                    "changes": [
                        {"value": _value}
                    ]
                }
            ]
        }
        events = provider.parse_webhook(single)

        for event in events:
            if isinstance(event, InboundMessage):
                await _handle_inbound_message(company_id, event)
            elif isinstance(event, StatusUpdate):
                await _handle_status_update(company_id, event)

    return {"status": "ok"}


async def _handle_inbound_message(company_id: UUID, msg: InboundMessage):
    """Process an incoming WhatsApp message (inside tenant context)."""
    logger.info(
        "inbound_message",
        company_id=str(company_id),
        from_number=msg.from_number,
        message_type=msg.message_type,
        message_id=msg.message_id,
    )

    async with tenant_session(company_id) as db:
        # Find contact by phone (RLS-filtered to this company)
        result = await db.execute(
            select(Contact).where(
                Contact.phone == msg.from_number,
                Contact.deleted_at.is_(None),
            ).limit(1)
        )
        contact = result.scalar_one_or_none()

        if not contact:
            contact = Contact(
                company_id=company_id,
                phone=msg.from_number,
                first_name=msg.contact_name or "",
                last_name="",
                source="whatsapp",
            )
            db.add(contact)
            await db.flush()
            logger.info("contact_auto_created", phone=msg.from_number)

        contact_id = contact.id

        # Get or create open conversation
        conv_result = await db.execute(
            select(Conversation).where(
                Conversation.company_id == company_id,
                Conversation.contact_id == contact_id,
                Conversation.status.in_(["open", "pending"]),
                Conversation.channel == "whatsapp",
            ).order_by(Conversation.created_at.desc()).limit(1)
        )
        conv = conv_result.scalar_one_or_none()

        if not conv:
            conv = Conversation(
                company_id=company_id,
                contact_id=contact_id,
                status="open",
                channel="whatsapp",
            )
            db.add(conv)
            await db.flush()

        # Extract content
        content = msg.content.get("body") if msg.message_type.value == "text" else None
        media_url = msg.content.get("media_id") if msg.message_type.value in ("image", "video", "audio", "document") else None

        # Add message
        message = Message(
            company_id=company_id,
            conversation_id=conv.id,
            direction="inbound",
            sender_type="contact",
            message_type=msg.message_type.value,
            content=content,
            media_url=media_url,
            external_id=msg.message_id,
            delivery_status="delivered",
            extra_data=msg.content if msg.message_type.value != "text" else None,
        )
        db.add(message)
        await db.flush()

        # Update conversation metadata
        now = datetime.now(timezone.utc)
        preview = (content or "")[:200] if content else f"[{msg.message_type.value}]"
        conv.last_message_at = now
        conv.last_message_preview = preview
        conv.unread_count = (conv.unread_count or 0) + 1

        # Update contact
        contact.last_contacted_at = now

        # Collect data for WebSocket before commit
        msg_data = {
            "id": str(message.id),
            "conversation_id": str(conv.id),
            "direction": "inbound",
            "sender_type": "contact",
            "message_type": msg.message_type.value,
            "content": content,
            "media_url": media_url,
            "external_id": msg.message_id,
            "delivery_status": "delivered",
            "created_at": message.created_at.isoformat(),
        }
        conv_data = {
            "id": str(conv.id),
            "contact_id": str(contact_id),
            "status": conv.status,
            "last_message_at": now.isoformat(),
            "last_message_preview": preview,
            "unread_count": conv.unread_count,
        }

        # Smart routing: auto-assign if unassigned
        if not conv.assigned_to_user_id:
            from app.services.routing_engine import RoutingEngine
            router = RoutingEngine(db, company_id)
            best_agent = await router.assign_conversation(conv)
            if best_agent:
                conv.assigned_to_user_id = best_agent

        conv_id = conv.id
        # tenant_session() commits on context exit

    # Trigger automations asynchronously
    from app.tasks.automation_tasks import evaluate_automation_event
    evaluate_automation_event.delay(
        company_id=str(company_id),
        event_type="message.received",
        event_data={
            "contact_id": str(contact_id),
            "conversation_id": str(conv_id),
            "message": {"content": content, "type": msg.message_type.value},
            "contact": {"phone": msg.from_number, "name": msg.contact_name},
        },
    )

    # Trigger AI analysis asynchronously
    if content:
        from app.tasks.ai_tasks import analyze_message_task
        analyze_message_task.delay(
            company_id=str(company_id),
            conversation_id=str(conv_id),
            message_content=content,
            direction="inbound",
        )

    # Broadcast outside the DB session
    await ws_manager.broadcast_to_company(company_id, {
        "type": "message.new",
        "data": msg_data,
    })
    await ws_manager.broadcast_to_company(company_id, {
        "type": "conversation.updated",
        "data": conv_data,
    })


async def _handle_status_update(company_id: UUID, status: StatusUpdate):
    """Process a delivery status update (inside tenant context)."""
    logger.info(
        "status_update",
        company_id=str(company_id),
        message_id=status.message_id,
        status=status.status,
    )

    async with tenant_session(company_id) as db:
        result = await db.execute(
            select(Message).where(Message.external_id == status.message_id)
        )
        msg = result.scalar_one_or_none()
        if not msg:
            return

        msg.delivery_status = status.status.value
        if status.error_message:
            msg.delivery_error = f"{status.error_code}: {status.error_message}"

        msg_id = str(msg.id)
        delivery_status = msg.delivery_status
        delivery_error = msg.delivery_error
        # tenant_session() commits on exit

    await ws_manager.broadcast_to_company(company_id, {
        "type": "message.status",
        "data": {
            "message_id": msg_id,
            "external_id": status.message_id,
            "delivery_status": delivery_status,
            "delivery_error": delivery_error,
        },
    })
