"""Facebook Messenger channel provider via Messenger Platform."""

from typing import Any
import httpx
import structlog
from app.services.channels.base import ChannelContact, ChannelMessage, ChannelProvider

logger = structlog.get_logger()
GRAPH_API = "https://graph.facebook.com/v19.0"


class FacebookMessengerProvider(ChannelProvider):
    def __init__(self, page_id: str, access_token: str):
        self.page_id = page_id
        self.access_token = access_token

    async def send_message(self, message: ChannelMessage) -> str:
        if not self.access_token:
            return f"fb_mock_{id(message)}"

        payload: dict[str, Any] = {
            "recipient": {"id": message.to_id},
            "messaging_type": "RESPONSE",
            "message": {},
        }
        if message.message_type == "text":
            payload["message"]["text"] = message.content
        elif message.message_type == "quick_reply":
            payload["message"]["text"] = message.content
            payload["message"]["quick_replies"] = message.metadata.get("quick_replies", []) if message.metadata else []
        elif message.message_type in ("image", "video", "audio", "file"):
            payload["message"]["attachment"] = {
                "type": message.message_type if message.message_type != "file" else "file",
                "payload": {"url": message.media_url, "is_reusable": True},
            }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GRAPH_API}/{self.page_id}/messages",
                json=payload,
                params={"access_token": self.access_token},
            )
            resp.raise_for_status()
            data = resp.json()
            mid = data.get("message_id", "")
            logger.info("facebook_message_sent", to=message.to_id, mid=mid)
            return mid

    def parse_webhook(self, payload: dict[str, Any]) -> list[ChannelMessage]:
        messages = []
        for entry in payload.get("entry", []):
            for messaging in entry.get("messaging", []):
                sender = messaging.get("sender", {}).get("id", "")
                msg = messaging.get("message", {})
                postback = messaging.get("postback", {})

                if msg:
                    content = msg.get("text")
                    msg_type = "text"
                    media_url = None
                    attachments = msg.get("attachments", [])
                    if attachments:
                        att = attachments[0]
                        msg_type = att.get("type", "image")
                        media_url = att.get("payload", {}).get("url")

                    messages.append(ChannelMessage(
                        from_id=sender, to_id=self.page_id, channel="facebook_messenger",
                        message_type=msg_type, content=content, media_url=media_url,
                        external_id=msg.get("mid"),
                    ))
                elif postback:
                    messages.append(ChannelMessage(
                        from_id=sender, to_id=self.page_id, channel="facebook_messenger",
                        message_type="postback", content=postback.get("title"),
                        metadata={"payload": postback.get("payload")},
                    ))
        return messages

    async def get_contact_info(self, channel_id: str) -> ChannelContact | None:
        if not self.access_token:
            return ChannelContact(channel_id=channel_id, name="FB User")

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GRAPH_API}/{channel_id}",
                params={"fields": "first_name,last_name,profile_pic", "access_token": self.access_token},
            )
            if resp.status_code == 200:
                data = resp.json()
                name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
                return ChannelContact(channel_id=channel_id, name=name, profile_pic=data.get("profile_pic"))
        return None
