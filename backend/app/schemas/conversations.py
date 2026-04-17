"""Schemas for conversations and messages."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import CamelModel
from app.schemas.contacts import ContactListItem


# ── Messages ──────────────────────────────────────────────────────────────────


class SendMessageRequest(CamelModel):
    conversation_id: UUID
    message_type: str = Field(default="text", pattern=r"^(text|image|video|audio|document|template|location)$")
    content: str | None = None
    media_url: str | None = None
    template_name: str | None = None
    template_language: str | None = Field(default="en", max_length=10)
    template_params: list[str] | None = None


class MessageResponse(CamelModel):
    id: UUID
    conversation_id: UUID
    direction: str
    sender_type: str
    sender_id: UUID | None = None
    message_type: str
    content: str | None = None
    media_url: str | None = None
    media_mime_type: str | None = None
    external_id: str | None = None
    delivery_status: str
    delivery_error: str | None = None
    created_at: datetime


# ── Conversations ─────────────────────────────────────────────────────────────


class ConversationResponse(CamelModel):
    id: UUID
    contact_id: UUID
    contact: ContactListItem | None = None
    status: str
    assigned_to_user_id: UUID | None = None
    last_message_at: datetime | None = None
    last_message_preview: str | None = None
    unread_count: int
    channel: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationResponse):
    messages: list[MessageResponse] = Field(default_factory=list)


class ConversationUpdate(CamelModel):
    status: str | None = Field(default=None, pattern=r"^(open|closed|pending|snoozed)$")
    assigned_to_user_id: UUID | None = None


class StartConversationRequest(CamelModel):
    contact_id: UUID
    message: str | None = None  # Optional initial message
