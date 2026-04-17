"""Conversation model - a thread between a contact and the company."""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class Conversation(Base, UUIDMixin, TimestampMixin, TenantMixin):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conv_company_status_last", "company_id", "status", "last_message_at"),
    )

    # Linked contact
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Status: open, closed, pending, snoozed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")

    # Assigned agent
    assigned_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Caching latest message info for fast list queries
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_message_preview: Mapped[str | None] = mapped_column(String(200), nullable=True)
    unread_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Channel (whatsapp, sms, etc.)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="whatsapp")

    # Relationships
    contact = relationship("Contact", lazy="noload")
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id], lazy="noload")
    messages = relationship(
        "Message", back_populates="conversation", lazy="noload",
        order_by="Message.created_at.desc()"
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.id} contact={self.contact_id}>"
