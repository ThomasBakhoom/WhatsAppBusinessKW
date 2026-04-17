"""Instagram Comment Lead Capture - converts post comments into WhatsApp conversations.

GAP 11: Automatically detect comments on Instagram posts, extract commenter info,
and create a WhatsApp conversation with the commenter.
"""

from typing import Any
from uuid import UUID

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact

logger = structlog.get_logger()

GRAPH_API = "https://graph.facebook.com/v19.0"


class InstagramCommentCapture:
    """Processes Instagram comment webhooks and converts commenters to leads."""

    def __init__(self, db: AsyncSession, company_id: UUID, access_token: str = ""):
        self.db = db
        self.company_id = company_id
        self.access_token = access_token

    def parse_comment_webhook(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse Instagram webhook for comment events.

        Instagram sends comment webhooks with this structure:
        {
          "entry": [{
            "changes": [{
              "field": "comments",
              "value": {
                "id": "comment_id",
                "text": "comment text",
                "from": {"id": "ig_user_id", "username": "user123"},
                "media": {"id": "media_id"},
                "timestamp": "..."
              }
            }]
          }]
        }
        """
        leads = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") != "comments":
                    continue

                value = change.get("value", {})
                commenter = value.get("from", {})
                ig_user_id = commenter.get("id", "")
                username = commenter.get("username", "")
                comment_text = value.get("text", "")
                media_id = value.get("media", {}).get("id", "")
                comment_id = value.get("id", "")

                if ig_user_id:
                    leads.append({
                        "ig_user_id": ig_user_id,
                        "username": username,
                        "comment_text": comment_text,
                        "comment_id": comment_id,
                        "media_id": media_id,
                        "source": "instagram_comment",
                    })

        return leads

    async def process_comment_lead(self, lead: dict[str, Any]) -> dict[str, Any]:
        """Process a comment lead: create/find contact, optionally auto-DM.

        Returns the created/found contact info and actions taken.
        """
        ig_user_id = lead["ig_user_id"]
        username = lead.get("username", "")
        comment_text = lead.get("comment_text", "")
        media_id = lead.get("media_id", "")

        # Get user profile info from Instagram Graph API
        profile = await self._get_ig_profile(ig_user_id)
        name = profile.get("name", username) if profile else username

        # Check if contact already exists (by Instagram ID in notes or custom field)
        existing = await self.db.execute(
            select(Contact).where(
                Contact.company_id == self.company_id,
                Contact.notes.ilike(f"%instagram:{ig_user_id}%"),
                Contact.deleted_at.is_(None),
            ).limit(1)
        )
        contact = existing.scalar_one_or_none()

        actions = []

        if not contact:
            # Create new contact from Instagram commenter
            contact = Contact(
                company_id=self.company_id,
                phone="",  # No phone yet - will be collected via DM
                first_name=name.split(" ")[0] if name else username,
                last_name=name.split(" ", 1)[1] if " " in (name or "") else "",
                source="instagram_comment",
                notes=f"instagram:{ig_user_id}\nusername:@{username}\nComment: {comment_text[:200]}",
            )
            self.db.add(contact)
            await self.db.flush()
            actions.append("contact_created")
            logger.info("ig_comment_lead_created", ig_user_id=ig_user_id, username=username)
        else:
            # Update notes with new comment
            contact.notes = (contact.notes or "") + f"\nComment on {media_id}: {comment_text[:200]}"
            actions.append("contact_updated")

        # Auto-DM the commenter (if access token available)
        if self.access_token and ig_user_id:
            dm_sent = await self._send_auto_dm(
                ig_user_id,
                f"Thanks for your comment! We'd love to help you. "
                f"Chat with us on WhatsApp for quick support."
            )
            if dm_sent:
                actions.append("auto_dm_sent")

        return {
            "contact_id": str(contact.id),
            "ig_user_id": ig_user_id,
            "username": username,
            "comment_text": comment_text[:100],
            "media_id": media_id,
            "actions": actions,
            "is_new": "contact_created" in actions,
        }

    async def _get_ig_profile(self, ig_user_id: str) -> dict | None:
        """Fetch Instagram user profile via Graph API."""
        if not self.access_token:
            return None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{GRAPH_API}/{ig_user_id}",
                    params={"fields": "name,profile_pic", "access_token": self.access_token},
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.error("ig_profile_fetch_failed", ig_user_id=ig_user_id, error=str(e))
        return None

    async def _send_auto_dm(self, ig_user_id: str, message: str) -> bool:
        """Send an automatic DM to the Instagram commenter."""
        if not self.access_token:
            logger.info("ig_auto_dm_mock", ig_user_id=ig_user_id, message=message[:50])
            return True  # Mock success in dev

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{GRAPH_API}/me/messages",
                    json={
                        "recipient": {"id": ig_user_id},
                        "message": {"text": message},
                    },
                    params={"access_token": self.access_token},
                )
                resp.raise_for_status()
                logger.info("ig_auto_dm_sent", ig_user_id=ig_user_id)
                return True
        except Exception as e:
            logger.error("ig_auto_dm_failed", ig_user_id=ig_user_id, error=str(e))
            return False
