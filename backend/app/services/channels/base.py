"""Abstract channel provider interface for omnichannel messaging."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ChannelMessage:
    """Unified message format across all channels."""
    from_id: str          # Sender identifier (phone, ig_user_id, fb_psid, etc.)
    to_id: str            # Recipient identifier
    channel: str          # whatsapp, instagram, facebook_messenger, web_chat, sms
    message_type: str     # text, image, video, audio, template, quick_reply
    content: str | None = None
    media_url: str | None = None
    media_type: str | None = None
    metadata: dict | None = None
    external_id: str | None = None


@dataclass
class ChannelContact:
    """Contact info from a channel."""
    channel_id: str       # Platform-specific user ID
    name: str | None = None
    profile_pic: str | None = None


class ChannelProvider(ABC):
    """Abstract interface for all messaging channel providers."""

    @abstractmethod
    async def send_message(self, message: ChannelMessage) -> str:
        """Send a message. Returns external message ID."""
        ...

    @abstractmethod
    def parse_webhook(self, payload: dict[str, Any]) -> list[ChannelMessage]:
        """Parse incoming webhook into unified messages."""
        ...

    @abstractmethod
    async def get_contact_info(self, channel_id: str) -> ChannelContact | None:
        """Get contact profile info from channel."""
        ...
