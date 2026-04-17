"""WhatsApp Cloud API provider implementation."""

import hashlib
import hmac
from typing import Any

import httpx
import structlog

from app.services.whatsapp.base import (
    DeliveryStatus,
    InboundMessage,
    MessageType,
    MessagingProvider,
    OutboundMessage,
    StatusUpdate,
)

logger = structlog.get_logger()

GRAPH_API_URL = "https://graph.facebook.com/v19.0"


class CloudAPIProvider(MessagingProvider):
    """WhatsApp Cloud API (Meta) provider."""

    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        verify_token: str,
        app_secret: str | None = None,
    ):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.verify_token = verify_token
        self.app_secret = app_secret
        self._client = httpx.AsyncClient(
            base_url=f"{GRAPH_API_URL}/{phone_number_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def send_message(self, message: OutboundMessage) -> str:
        """Send a message via Cloud API. Returns the WhatsApp message ID."""
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": message.to,
        }

        if message.message_type == MessageType.TEXT:
            payload["type"] = "text"
            payload["text"] = {"body": message.content.get("body", "")}
        elif message.message_type == MessageType.TEMPLATE:
            payload["type"] = "template"
            payload["template"] = message.content
        elif message.message_type in (
            MessageType.IMAGE, MessageType.VIDEO,
            MessageType.AUDIO, MessageType.DOCUMENT,
        ):
            media_type = message.message_type.value
            payload["type"] = media_type
            payload[media_type] = message.content
        elif message.message_type == MessageType.LOCATION:
            payload["type"] = "location"
            payload["location"] = message.content
        elif message.message_type == MessageType.INTERACTIVE:
            payload["type"] = "interactive"
            payload["interactive"] = message.content
        else:
            payload["type"] = "text"
            payload["text"] = {"body": str(message.content)}

        response = await self._client.post("/messages", json=payload)
        response.raise_for_status()
        data = response.json()

        wa_message_id = data["messages"][0]["id"]
        logger.info(
            "whatsapp_message_sent",
            to=message.to,
            message_id=wa_message_id,
            message_type=message.message_type,
        )
        return wa_message_id

    async def send_template(
        self,
        to: str,
        template_name: str,
        language: str,
        params: list[str] | None = None,
    ) -> str:
        """Send a template message."""
        template_payload: dict[str, Any] = {
            "name": template_name,
            "language": {"code": language},
        }
        if params:
            template_payload["components"] = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": p} for p in params
                    ],
                }
            ]

        message = OutboundMessage(
            to=to,
            message_type=MessageType.TEMPLATE,
            content=template_payload,
            template_name=template_name,
            template_language=language,
            template_params=params,
        )
        return await self.send_message(message)

    def parse_webhook(self, payload: dict[str, Any]) -> list[InboundMessage | StatusUpdate]:
        """Parse Cloud API webhook payload into messages and status updates."""
        results: list[InboundMessage | StatusUpdate] = []

        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                # Parse incoming messages
                for msg in value.get("messages", []):
                    msg_type = msg.get("type", "text")
                    content = self._extract_content(msg, msg_type)
                    contact_name = None
                    contacts = value.get("contacts", [])
                    if contacts:
                        profile = contacts[0].get("profile", {})
                        contact_name = profile.get("name")

                    results.append(
                        InboundMessage(
                            from_number=msg["from"],
                            message_id=msg["id"],
                            message_type=MessageType(msg_type) if msg_type in MessageType.__members__.values() else MessageType.TEXT,
                            content=content,
                            timestamp=msg.get("timestamp", ""),
                            contact_name=contact_name,
                        )
                    )

                # Parse status updates
                for status in value.get("statuses", []):
                    status_map = {
                        "sent": DeliveryStatus.SENT,
                        "delivered": DeliveryStatus.DELIVERED,
                        "read": DeliveryStatus.READ,
                        "failed": DeliveryStatus.FAILED,
                    }
                    ds = status_map.get(status["status"], DeliveryStatus.SENT)

                    error_code = None
                    error_message = None
                    errors = status.get("errors", [])
                    if errors:
                        error_code = str(errors[0].get("code", ""))
                        error_message = errors[0].get("title", "")

                    results.append(
                        StatusUpdate(
                            message_id=status["id"],
                            status=ds,
                            timestamp=status.get("timestamp", ""),
                            error_code=error_code,
                            error_message=error_message,
                        )
                    )

        return results

    def verify_webhook(self, request_data: dict[str, Any]) -> bool:
        """Verify webhook subscription (GET) or payload signature (POST)."""
        # GET verification (subscription)
        if "hub.mode" in request_data:
            return (
                request_data.get("hub.mode") == "subscribe"
                and request_data.get("hub.verify_token") == self.verify_token
            )

        # POST signature verification
        if self.app_secret and "x_hub_signature_256" in request_data:
            signature = request_data["x_hub_signature_256"]
            body = request_data.get("raw_body", b"")
            expected = "sha256=" + hmac.new(
                self.app_secret.encode(), body, hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected)

        return True  # No signature verification configured

    def _extract_content(self, msg: dict, msg_type: str) -> dict[str, Any]:
        """Extract content from a webhook message by type."""
        if msg_type == "text":
            return {"body": msg.get("text", {}).get("body", "")}
        elif msg_type in ("image", "video", "audio", "document"):
            media = msg.get(msg_type, {})
            return {
                "media_id": media.get("id"),
                "mime_type": media.get("mime_type"),
                "caption": media.get("caption"),
                "filename": media.get("filename"),
            }
        elif msg_type == "location":
            loc = msg.get("location", {})
            return {
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
                "name": loc.get("name"),
                "address": loc.get("address"),
            }
        elif msg_type == "interactive":
            return msg.get("interactive", {})
        else:
            return {"raw": msg}

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
