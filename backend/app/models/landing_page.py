"""Landing page model - builder pages with WhatsApp CTA."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TenantMixin, TimestampMixin, UUIDMixin


class LandingPage(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """A landing page with block-based content and WhatsApp CTA."""

    __tablename__ = "landing_pages"
    __table_args__ = (
        Index("ix_lp_slug", "slug", unique=True),
    )

    # Page identity
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )  # draft, published, archived
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Content blocks (TipTap-style JSON)
    # [{type: "hero", content: {...}}, {type: "text", content: {...}}, ...]
    blocks: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")

    # Page settings
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    # settings: {
    #   whatsapp_number, whatsapp_message, primary_color, font,
    #   meta_title, meta_description, og_image, favicon,
    #   custom_css, custom_js, header_code, footer_code
    # }

    # WhatsApp CTA
    whatsapp_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    whatsapp_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Analytics
    visit_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    conversion_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    # SEO
    meta_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    og_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Template
    template: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def __repr__(self) -> str:
        return f"<LandingPage {self.slug} ({self.status})>"
