"""Snapchat Lead Generation integration."""

from typing import Any
import httpx
import structlog
from app.services.channels.base import ChannelContact, ChannelMessage, ChannelProvider

logger = structlog.get_logger()


class SnapchatLeadProvider(ChannelProvider):
    """Snapchat Lead Gen webhook receiver - converts Snap ad leads to contacts."""

    def __init__(self, pixel_id: str = "", access_token: str = ""):
        self.pixel_id = pixel_id
        self.access_token = access_token

    async def send_message(self, message: ChannelMessage) -> str:
        # Snapchat is inbound-only (lead capture), no outbound messaging
        logger.warning("snapchat_send_not_supported")
        return ""

    def parse_webhook(self, payload: dict[str, Any]) -> list[ChannelMessage]:
        """Parse Snapchat Lead Gen webhook into lead contact data."""
        leads = []
        for lead in payload.get("leads", []):
            name = lead.get("name", "")
            phone = lead.get("phone_number", "")
            email = lead.get("email", "")
            ad_id = lead.get("ad_id", "")
            campaign = lead.get("campaign_name", "")

            if phone:
                leads.append(ChannelMessage(
                    from_id=phone, to_id="", channel="snapchat",
                    message_type="lead", content=f"Snapchat lead: {name}",
                    metadata={
                        "name": name, "phone": phone, "email": email,
                        "ad_id": ad_id, "campaign": campaign,
                        "source": "snapchat_ad",
                    },
                ))
        return leads

    async def get_contact_info(self, channel_id: str) -> ChannelContact | None:
        return ChannelContact(channel_id=channel_id, name="Snapchat Lead")
