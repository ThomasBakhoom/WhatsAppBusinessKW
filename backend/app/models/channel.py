"""Omnichannel models - Instagram, Facebook Messenger, Web Chat, SMS."""

import uuid
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class Channel(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """A configured messaging channel for a company."""

    __tablename__ = "channels"

    # whatsapp, instagram, facebook_messenger, web_chat, sms, email
    channel_type: Mapped[str] = mapped_column(String(30), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Channel-specific credentials and config
    credentials: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    # WhatsApp: {phone_number_id, access_token, business_account_id}
    # Instagram: {page_id, access_token, ig_user_id}
    # Facebook: {page_id, access_token}
    # Web Chat: {widget_id, allowed_domains}
    # SMS: {provider, api_key, sender_number}

    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    # {welcome_message, auto_reply, business_hours, ...}

    def __repr__(self) -> str:
        return f"<Channel {self.channel_type} ({self.display_name})>"


class WebChatWidget(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Web chat widget configuration for embedding on websites."""

    __tablename__ = "web_chat_widgets"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # Appearance
    primary_color: Mapped[str] = mapped_column(String(7), default="#25D366")
    position: Mapped[str] = mapped_column(String(20), default="bottom-right")
    welcome_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    placeholder_text: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Allowed domains
    allowed_domains: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")

    # Embed code reference
    widget_token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    def __repr__(self) -> str:
        return f"<WebChatWidget {self.name}>"
