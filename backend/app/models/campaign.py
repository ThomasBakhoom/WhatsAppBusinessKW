"""Campaign/Broadcast models - bulk WhatsApp messaging."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class Campaign(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """A broadcast campaign to send bulk WhatsApp messages."""

    __tablename__ = "campaigns"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status: draft, scheduled, sending, sent, paused, cancelled
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    # Message content
    message_type: Mapped[str] = mapped_column(String(20), nullable=False, default="template")  # template, text
    template_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    template_language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    message_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Audience targeting
    audience_type: Mapped[str] = mapped_column(String(30), nullable=False, default="all")  # all, tag, segment, custom
    audience_filter: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    # e.g., {"tag_ids": [...], "status": "active", "source": "whatsapp"}

    # Scheduling
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Stats
    total_recipients: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    sent_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    delivered_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    read_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    failed_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reply_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # Created by
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )

    # Relationships
    recipients = relationship("CampaignRecipient", back_populates="campaign", lazy="noload")

    def __repr__(self) -> str:
        return f"<Campaign {self.name} ({self.status})>"


class CampaignRecipient(Base, UUIDMixin, TimestampMixin):
    """Individual recipient status in a campaign."""

    __tablename__ = "campaign_recipients"
    __table_args__ = (
        Index("ix_camp_recip_campaign", "campaign_id"),
    )

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False,
    )
    phone: Mapped[str] = mapped_column(String(20), nullable=False)

    # Status: pending, sent, delivered, read, failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    external_message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    campaign = relationship("Campaign", back_populates="recipients")

    def __repr__(self) -> str:
        return f"<CampaignRecipient {self.phone} ({self.status})>"
