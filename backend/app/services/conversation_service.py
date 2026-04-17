"""Conversation and messaging service."""

from datetime import datetime, timezone
from uuid import UUID

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.contact import Contact, ContactTag
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.conversations import (
    ConversationDetail,
    ConversationResponse,
    ConversationUpdate,
    MessageResponse,
)
from app.schemas.contacts import ContactListItem, TagResponse
from app.services.actor import Actor
from app.services.audit_service import AuditService

logger = structlog.get_logger()


class ConversationService:
    def __init__(
        self,
        db: AsyncSession,
        company_id: UUID,
        actor: Actor | None = None,
    ):
        self.db = db
        self.company_id = company_id
        self.actor = actor
        self._audit = AuditService(db, company_id, actor=actor)

    async def list_conversations(
        self,
        *,
        status: str | None = None,
        assigned_to: UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ConversationResponse], int]:
        """List conversations ordered by last message."""
        base = select(Conversation).where(
            Conversation.company_id == self.company_id
        )

        if status:
            base = base.where(Conversation.status == status)
        if assigned_to:
            base = base.where(Conversation.assigned_to_user_id == assigned_to)

        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        query = (
            base.options(
                selectinload(Conversation.contact)
                .selectinload(Contact.tags).selectinload(ContactTag.tag)
            )
            .order_by(Conversation.last_message_at.desc().nullslast())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        conversations = result.scalars().unique().all()

        items = [self._to_response(c) for c in conversations]
        return items, total

    async def get_conversation(
        self, conversation_id: UUID, message_limit: int = 50
    ) -> ConversationDetail:
        """Get a conversation with its recent messages."""
        conv = await self._get_or_404(conversation_id)

        # Load messages separately for pagination control
        msg_q = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(message_limit)
        )
        msg_result = await self.db.execute(msg_q)
        messages = list(reversed(msg_result.scalars().all()))

        # Mark as read (reset unread)
        conv.unread_count = 0
        await self.db.flush()

        resp = self._to_response(conv)
        return ConversationDetail(
            **resp.model_dump(),
            messages=[self._msg_to_response(m) for m in messages],
        )

    async def get_or_create_conversation(
        self, contact_id: UUID, channel: str = "whatsapp"
    ) -> Conversation:
        """Get an open conversation for a contact, or create one."""
        result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.company_id == self.company_id,
                Conversation.contact_id == contact_id,
                Conversation.status.in_(["open", "pending"]),
                Conversation.channel == channel,
            )
            .options(selectinload(Conversation.contact))
            .order_by(Conversation.created_at.desc())
            .limit(1)
        )
        conv = result.scalar_one_or_none()

        if not conv:
            conv = Conversation(
                company_id=self.company_id,
                contact_id=contact_id,
                status="open",
                channel=channel,
            )
            self.db.add(conv)
            await self.db.flush()
            # Reload with relationships
            result = await self.db.execute(
                select(Conversation)
                .where(Conversation.id == conv.id)
                .options(selectinload(Conversation.contact))
            )
            conv = result.scalar_one()

        return conv

    async def update_conversation(
        self, conversation_id: UUID, data: ConversationUpdate
    ) -> ConversationResponse:
        """Update conversation status or assignment.

        Audited fields: status (open/closed/etc), assigned_to_user_id.
        Other field churn (priority, tags) is captured but not classified.
        """
        conv = await self._get_or_404(conversation_id)
        update_data = data.model_dump(exclude_unset=True)

        diff: dict[str, dict] = {}
        # Pick the most operationally meaningful field-level audit actions.
        action = "conversation.updated"
        if "status" in update_data and update_data["status"] != conv.status:
            action = "conversation.status_changed"
        elif (
            "assigned_to_user_id" in update_data
            and update_data["assigned_to_user_id"] != conv.assigned_to_user_id
        ):
            action = "conversation.assigned"

        for key, new_value in update_data.items():
            old = getattr(conv, key, None)
            if old != new_value:
                diff[key] = {
                    "old": str(old) if old is not None else None,
                    "new": str(new_value) if new_value is not None else None,
                }
            setattr(conv, key, new_value)

        await self.db.flush()

        if diff:
            await self._audit.log(
                action=action,
                description=f"Conversation {conversation_id} {action.split('.')[-1]}",
                resource_type="conversation",
                resource_id=str(conv.id),
                changes=diff,
            )

        return self._to_response(conv)

    async def add_message(
        self,
        conversation_id: UUID,
        *,
        direction: str,
        sender_type: str,
        sender_id: UUID | None = None,
        message_type: str = "text",
        content: str | None = None,
        media_url: str | None = None,
        media_mime_type: str | None = None,
        external_id: str | None = None,
        delivery_status: str = "pending",
        extra_data: dict | None = None,
    ) -> Message:
        """Add a message to a conversation and update conversation metadata."""
        msg = Message(
            company_id=self.company_id,
            conversation_id=conversation_id,
            direction=direction,
            sender_type=sender_type,
            sender_id=sender_id,
            message_type=message_type,
            content=content,
            media_url=media_url,
            media_mime_type=media_mime_type,
            external_id=external_id,
            delivery_status=delivery_status,
            extra_data=extra_data,
        )
        self.db.add(msg)
        await self.db.flush()

        # Update conversation last message info
        preview = (content or "")[:200] if content else f"[{message_type}]"
        now = datetime.now(timezone.utc)

        await self.db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(
                last_message_at=now,
                last_message_preview=preview,
                unread_count=(
                    Conversation.unread_count + 1
                    if direction == "inbound"
                    else Conversation.unread_count
                ),
            )
        )

        return msg

    async def update_delivery_status(
        self, external_id: str, status: str, error: str | None = None
    ) -> Message | None:
        """Update delivery status of a message by its external ID."""
        result = await self.db.execute(
            select(Message).where(
                Message.external_id == external_id,
                Message.company_id == self.company_id,
            )
        )
        msg = result.scalar_one_or_none()
        if not msg:
            return None

        msg.delivery_status = status
        if error:
            msg.delivery_error = error
        await self.db.flush()
        return msg

    async def get_messages(
        self, conversation_id: UUID, *, limit: int = 50, before: datetime | None = None
    ) -> list[MessageResponse]:
        """Get messages for a conversation with cursor-based pagination."""
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
        )
        if before:
            query = query.where(Message.created_at < before)

        query = query.order_by(Message.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        messages = list(reversed(result.scalars().all()))
        return [self._msg_to_response(m) for m in messages]

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _get_or_404(self, conversation_id: UUID) -> Conversation:
        result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.company_id == self.company_id,
                Conversation.id == conversation_id,
            )
            .options(
                selectinload(Conversation.contact)
                .selectinload(Contact.tags).selectinload(ContactTag.tag)
            )
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise NotFoundError("Conversation not found")
        return conv

    def _to_response(self, conv: Conversation) -> ConversationResponse:
        contact_item = None
        if conv.contact:
            from app.models.contact import ContactTag
            contact_item = ContactListItem(
                id=conv.contact.id,
                phone=conv.contact.phone,
                email=conv.contact.email,
                first_name=conv.contact.first_name,
                last_name=conv.contact.last_name,
                full_name=conv.contact.full_name,
                status=conv.contact.status,
                source=conv.contact.source,
                lead_score=conv.contact.lead_score,
                opt_in_whatsapp=conv.contact.opt_in_whatsapp,
                last_contacted_at=conv.contact.last_contacted_at,
                assigned_to_user_id=conv.contact.assigned_to_user_id,
                tags=[
                    TagResponse(
                        id=ct.tag.id, name=ct.tag.name, color=ct.tag.color,
                        description=ct.tag.description,
                        created_at=ct.tag.created_at, updated_at=ct.tag.updated_at,
                    )
                    for ct in conv.contact.tags if ct.tag
                ],
                created_at=conv.contact.created_at,
            )
        return ConversationResponse(
            id=conv.id,
            contact_id=conv.contact_id,
            contact=contact_item,
            status=conv.status,
            assigned_to_user_id=conv.assigned_to_user_id,
            last_message_at=conv.last_message_at,
            last_message_preview=conv.last_message_preview,
            unread_count=conv.unread_count,
            channel=conv.channel,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )

    def _msg_to_response(self, msg: Message) -> MessageResponse:
        return MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            direction=msg.direction,
            sender_type=msg.sender_type,
            sender_id=msg.sender_id,
            message_type=msg.message_type,
            content=msg.content,
            media_url=msg.media_url,
            media_mime_type=msg.media_mime_type,
            external_id=msg.external_id,
            delivery_status=msg.delivery_status,
            delivery_error=msg.delivery_error,
            created_at=msg.created_at,
        )
