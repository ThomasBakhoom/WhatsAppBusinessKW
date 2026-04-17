"""Conversation and messaging API endpoints."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Query, Request
from sqlalchemy import select

from app.core.pagination import PaginatedResponse
from app.dependencies import AuthUser, TenantDbSession
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.conversations import (
    ConversationDetail,
    ConversationResponse,
    ConversationUpdate,
    MessageResponse,
    SendMessageRequest,
    StartConversationRequest,
)
from app.services.actor import actor_from_request
from app.services.conversation_service import ConversationService
from app.websocket.manager import ws_manager

logger = structlog.get_logger()
router = APIRouter()


@router.get("", response_model=PaginatedResponse[ConversationResponse])
async def list_conversations(
    db: TenantDbSession,
    user: AuthUser,
    status: str | None = Query(default=None, pattern=r"^(open|closed|pending|snoozed)$"),
    assigned_to: UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List conversations, most recent first."""
    svc = ConversationService(db, user.company_id)
    items, total = await svc.list_conversations(
        status=status, assigned_to=assigned_to, limit=limit, offset=offset,
    )
    return PaginatedResponse.create(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=ConversationResponse, status_code=201)
async def start_conversation(
    data: StartConversationRequest,
    db: TenantDbSession,
    user: AuthUser,
):
    """Start or resume a conversation with a contact."""
    svc = ConversationService(db, user.company_id)
    conv = await svc.get_or_create_conversation(data.contact_id)

    if data.message:
        msg = await svc.add_message(
            conv.id,
            direction="outbound",
            sender_type="agent",
            sender_id=user.user_id,
            message_type="text",
            content=data.message,
            delivery_status="pending",
        )

        # Dispatch send task
        contact_result = await db.execute(
            select(Contact).where(Contact.id == data.contact_id)
        )
        contact = contact_result.scalar_one_or_none()
        if contact:
            from app.tasks.messaging_tasks import send_whatsapp_message
            send_whatsapp_message.delay(
                message_id=str(msg.id),
                company_id=str(user.company_id),
                to=contact.phone,
                message_type="text",
                content=data.message,
            )

    await db.commit()
    return svc._to_response(conv)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    db: TenantDbSession,
    user: AuthUser,
    message_limit: int = Query(default=50, ge=1, le=200),
):
    """Get a conversation with its messages."""
    svc = ConversationService(db, user.company_id)
    detail = await svc.get_conversation(conversation_id, message_limit=message_limit)
    await db.commit()
    return detail


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    data: ConversationUpdate,
    request: Request,
    db: TenantDbSession,
    user: AuthUser,
):
    """Update conversation status or assignment."""
    svc = ConversationService(db, user.company_id, actor=actor_from_request(user, request))
    conv = await svc.update_conversation(conversation_id, data)
    await db.commit()

    await ws_manager.broadcast_to_company(user.company_id, {
        "type": "conversation.updated",
        "data": conv.model_dump(mode="json"),
    })
    return conv


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: UUID,
    db: TenantDbSession,
    user: AuthUser,
    limit: int = Query(default=50, ge=1, le=200),
    before: str | None = Query(default=None),
):
    """Get messages for a conversation."""
    svc = ConversationService(db, user.company_id)
    before_dt = None
    if before:
        from datetime import datetime
        before_dt = datetime.fromisoformat(before)
    return await svc.get_messages(conversation_id, limit=limit, before=before_dt)


@router.post("/messages/send", response_model=MessageResponse, status_code=201)
async def send_message(
    data: SendMessageRequest,
    db: TenantDbSession,
    user: AuthUser,
):
    """Send a message in a conversation."""
    svc = ConversationService(db, user.company_id)

    msg = await svc.add_message(
        data.conversation_id,
        direction="outbound",
        sender_type="agent",
        sender_id=user.user_id,
        message_type=data.message_type,
        content=data.content,
        media_url=data.media_url,
        delivery_status="pending",
    )
    await db.commit()

    # Dispatch to WhatsApp via Celery
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == data.conversation_id)
    )
    conv = conv_result.scalar_one_or_none()
    if conv:
        contact_result = await db.execute(
            select(Contact).where(Contact.id == conv.contact_id)
        )
        contact = contact_result.scalar_one_or_none()
        if contact:
            from app.tasks.messaging_tasks import send_whatsapp_message
            send_whatsapp_message.delay(
                message_id=str(msg.id),
                company_id=str(user.company_id),
                to=contact.phone,
                message_type=data.message_type,
                content=data.content,
                media_url=data.media_url,
                template_name=data.template_name,
                template_language=data.template_language,
                template_params=data.template_params,
            )

    # Broadcast via WebSocket
    msg_response = svc._msg_to_response(msg)
    await ws_manager.broadcast_to_company(user.company_id, {
        "type": "message.new",
        "data": msg_response.model_dump(mode="json"),
    })

    return msg_response
