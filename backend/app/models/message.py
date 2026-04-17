"""Message and MessageTemplate models."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class Message(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_msg_conv_created", "conversation_id", "created_at"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Direction: inbound (from contact) or outbound (from agent/system)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # inbound, outbound

    # Sender info
    sender_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="contact"
    )  # contact, agent, system, bot
    sender_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )  # user_id for agents

    # Content
    message_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="text"
    )  # text, image, video, audio, document, template, interactive, location
    content: Mapped[str | None] = mapped_column(Text, nullable=True)  # text body
    media_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # extra metadata

    # External provider tracking
    external_id: Mapped[str | None] = mapped_column(
        String(200), nullable=True, index=True
    )  # WhatsApp message ID
    delivery_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, sent, delivered, read, failed
    delivery_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message {self.id} {self.direction} {self.message_type}>"


class MessageTemplate(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "message_templates"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    category: Mapped[str] = mapped_column(
        String(30), nullable=False, default="MARKETING"
    )  # MARKETING, UTILITY, AUTHENTICATION
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )  # draft, pending, approved, rejected

    # Template content
    header_type: Mapped[str | None] = mapped_column(String(10), nullable=True)  # text, image, video, document
    header_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    footer: Mapped[str | None] = mapped_column(Text, nullable=True)
    buttons: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # WhatsApp sync
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)

    def __repr__(self) -> str:
        return f"<MessageTemplate {self.name} ({self.status})>"
