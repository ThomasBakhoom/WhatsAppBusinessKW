"""Company (tenant) model."""

import uuid

from sqlalchemy import String, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class Company(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "companies"

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # WhatsApp configuration (encrypted at application level)
    whatsapp_phone_number_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    whatsapp_business_account_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    whatsapp_api_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Twilio fallback
    twilio_account_sid: Mapped[str | None] = mapped_column(String(50), nullable=True)
    twilio_auth_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Payment configuration
    tap_merchant_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tap_secret_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Settings (flexible JSON)
    settings: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        default=dict,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # Relationships
    users = relationship("User", back_populates="company", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Company {self.name} ({self.slug})>"
