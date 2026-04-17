"""Channel router - routes messages to/from the correct provider."""

from uuid import UUID
from typing import Any
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.channel import Channel
from app.services.channels.base import ChannelMessage, ChannelProvider
from app.services.channels.instagram import InstagramProvider
from app.services.channels.facebook import FacebookMessengerProvider

logger = structlog.get_logger()


class ChannelRouter:
    """Routes messages to the correct channel provider."""

    def __init__(self, db: AsyncSession, company_id: UUID):
        self.db = db
        self.company_id = company_id

    async def get_provider(self, channel_type: str) -> ChannelProvider | None:
        """Get the configured provider for a channel type."""
        result = await self.db.execute(
            select(Channel).where(
                Channel.company_id == self.company_id,
                Channel.channel_type == channel_type,
                Channel.is_active == True,
            ).limit(1)
        )
        channel = result.scalar_one_or_none()
        if not channel:
            return None

        creds = channel.credentials or {}

        if channel_type == "instagram":
            return InstagramProvider(
                page_id=creds.get("page_id", ""),
                access_token=creds.get("access_token", ""),
            )
        elif channel_type == "facebook_messenger":
            return FacebookMessengerProvider(
                page_id=creds.get("page_id", ""),
                access_token=creds.get("access_token", ""),
            )
        # WhatsApp uses its own provider (CloudAPIProvider)
        return None

    async def send(self, channel_type: str, message: ChannelMessage) -> str | None:
        """Send a message via the correct channel provider."""
        provider = await self.get_provider(channel_type)
        if not provider:
            logger.warning("no_provider_for_channel", channel=channel_type)
            return None

        try:
            external_id = await provider.send_message(message)
            logger.info("channel_message_sent", channel=channel_type, external_id=external_id)
            return external_id
        except Exception as e:
            logger.error("channel_send_failed", channel=channel_type, error=str(e))
            return None

    async def parse_inbound(self, channel_type: str, payload: dict[str, Any]) -> list[ChannelMessage]:
        """Parse an inbound webhook for any channel."""
        provider = await self.get_provider(channel_type)
        if not provider:
            return []
        return provider.parse_webhook(payload)
