"""Abstract messaging provider interface.

This abstraction allows swapping between WhatsApp Cloud API (primary)
and Twilio (fallback) via configuration, without changing business logic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class MessageType(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    TEMPLATE = "template"
    INTERACTIVE = "interactive"
    LOCATION = "location"


class DeliveryStatus(StrEnum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


@dataclass
class OutboundMessage:
    """A message to be sent via WhatsApp."""
    to: str  # E.164 phone number
    message_type: MessageType
    content: dict[str, Any]  # Type-specific content
    template_name: str | None = None
    template_language: str | None = None
    template_params: list[str] | None = None


@dataclass
class InboundMessage:
    """A message received from WhatsApp."""
    from_number: str
    message_id: str
    message_type: MessageType
    content: dict[str, Any]
    timestamp: str
    contact_name: str | None = None


@dataclass
class StatusUpdate:
    """A delivery status update from WhatsApp."""
    message_id: str
    status: DeliveryStatus
    timestamp: str
    error_code: str | None = None
    error_message: str | None = None


class MessagingProvider(ABC):
    """Abstract interface for WhatsApp messaging providers."""

    @abstractmethod
    async def send_message(self, message: OutboundMessage) -> str:
        """
        Send a WhatsApp message.

        Returns the external message ID from the provider.
        """
        ...

    @abstractmethod
    async def send_template(
        self,
        to: str,
        template_name: str,
        language: str,
        params: list[str] | None = None,
    ) -> str:
        """Send a template message. Returns external message ID."""
        ...

    @abstractmethod
    def parse_webhook(self, payload: dict[str, Any]) -> list[InboundMessage | StatusUpdate]:
        """
        Parse an incoming webhook payload from the provider.

        Returns a list of inbound messages and/or status updates.
        """
        ...

    @abstractmethod
    def verify_webhook(self, request_data: dict[str, Any]) -> bool:
        """Verify that a webhook request is authentic."""
        ...
