"""Twilio WhatsApp fallback provider."""

from typing import Any
import httpx
import structlog
from app.services.whatsapp.base import (
    DeliveryStatus, InboundMessage, MessageType, MessagingProvider,
    OutboundMessage, StatusUpdate,
)

logger = structlog.get_logger()


class TwilioProvider(MessagingProvider):
    """Twilio WhatsApp Business API provider (fallback)."""

    def __init__(self, account_sid: str, auth_token: str, whatsapp_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.whatsapp_number = whatsapp_number
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}"

    async def send_message(self, message: OutboundMessage) -> str:
        if not self.account_sid:
            return f"twilio_mock_{id(message)}"

        to_number = f"whatsapp:{message.to}"
        from_number = f"whatsapp:{self.whatsapp_number}"

        data = {"To": to_number, "From": from_number}

        if message.message_type == MessageType.TEXT:
            data["Body"] = message.content.get("body", "")
        elif message.message_type == MessageType.TEMPLATE:
            data["ContentSid"] = message.content.get("content_sid", "")
            if message.template_params:
                data["ContentVariables"] = str(dict(enumerate(message.template_params, 1)))
        elif message.message_type in (MessageType.IMAGE, MessageType.VIDEO, MessageType.DOCUMENT):
            data["MediaUrl"] = message.content.get("link", "")
            if message.content.get("caption"):
                data["Body"] = message.content["caption"]

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/Messages.json",
                data=data,
                auth=(self.account_sid, self.auth_token),
            )
            resp.raise_for_status()
            result = resp.json()
            sid = result["sid"]
            logger.info("twilio_message_sent", to=message.to, sid=sid)
            return sid

    async def send_template(self, to: str, template_name: str, language: str,
                            params: list[str] | None = None) -> str:
        msg = OutboundMessage(
            to=to, message_type=MessageType.TEMPLATE,
            content={"content_sid": template_name},
            template_name=template_name, template_language=language,
            template_params=params,
        )
        return await self.send_message(msg)

    def parse_webhook(self, payload: dict[str, Any]) -> list[InboundMessage | StatusUpdate]:
        results: list[InboundMessage | StatusUpdate] = []
        if "Body" in payload:
            results.append(InboundMessage(
                from_number=payload.get("From", "").replace("whatsapp:", ""),
                message_id=payload.get("MessageSid", ""),
                message_type=MessageType.TEXT,
                content={"body": payload.get("Body", "")},
                timestamp=payload.get("DateCreated", ""),
                contact_name=payload.get("ProfileName"),
            ))
        if "MessageStatus" in payload:
            status_map = {
                "sent": DeliveryStatus.SENT, "delivered": DeliveryStatus.DELIVERED,
                "read": DeliveryStatus.READ, "failed": DeliveryStatus.FAILED,
                "undelivered": DeliveryStatus.FAILED,
            }
            results.append(StatusUpdate(
                message_id=payload.get("MessageSid", ""),
                status=status_map.get(payload["MessageStatus"], DeliveryStatus.SENT),
                timestamp=payload.get("DateUpdated", ""),
                error_code=payload.get("ErrorCode"),
                error_message=payload.get("ErrorMessage"),
            ))
        return results

    def verify_webhook(self, request_data: dict[str, Any]) -> bool:
        return True  # Twilio uses request signing - full impl needs twilio SDK
