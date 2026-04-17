"""Unified cross-channel interaction timeline for a contact."""

from uuid import UUID
from fastapi import APIRouter, Query
from sqlalchemy import select, union_all, literal, cast, String
from app.dependencies import AuthUser, TenantDbSession
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.pipeline import Deal, DealActivity
from app.models.shipping import Shipment

router = APIRouter()


@router.get("/{contact_id}")
async def get_contact_timeline(
    contact_id: UUID, db: TenantDbSession, user: AuthUser,
    limit: int = Query(default=50, ge=1, le=200),
):
    """Unified timeline of all interactions with a contact across all channels."""
    timeline = []

    # Messages (WhatsApp, Instagram, etc.)
    msg_result = await db.execute(
        select(Message).join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.contact_id == contact_id, Conversation.company_id == user.company_id)
        .order_by(Message.created_at.desc()).limit(limit)
    )
    for m in msg_result.scalars().all():
        timeline.append({
            "type": "message", "id": str(m.id),
            "direction": m.direction, "sender_type": m.sender_type,
            "message_type": m.message_type, "content": m.content,
            "channel": "whatsapp", "delivery_status": m.delivery_status,
            "timestamp": m.created_at.isoformat(),
        })

    # Conversations (open/close events)
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.contact_id == contact_id, Conversation.company_id == user.company_id
        ).order_by(Conversation.created_at.desc()).limit(20)
    )
    for c in conv_result.scalars().all():
        timeline.append({
            "type": "conversation", "id": str(c.id),
            "status": c.status, "channel": c.channel,
            "content": f"Conversation {c.status}",
            "timestamp": c.created_at.isoformat(),
        })

    # Deal activities
    deal_result = await db.execute(
        select(Deal).where(
            Deal.contact_id == contact_id, Deal.company_id == user.company_id, Deal.deleted_at.is_(None)
        )
    )
    for deal in deal_result.scalars().all():
        act_result = await db.execute(
            select(DealActivity).where(DealActivity.deal_id == deal.id)
            .order_by(DealActivity.created_at.desc()).limit(20)
        )
        for a in act_result.scalars().all():
            timeline.append({
                "type": "deal_activity", "id": str(a.id),
                "activity_type": a.activity_type, "content": a.description,
                "deal_title": deal.title, "deal_id": str(deal.id),
                "timestamp": a.created_at.isoformat(),
            })

    # Shipments
    ship_result = await db.execute(
        select(Shipment).where(
            Shipment.contact_id == contact_id, Shipment.company_id == user.company_id
        ).order_by(Shipment.created_at.desc()).limit(10)
    )
    for s in ship_result.scalars().all():
        timeline.append({
            "type": "shipment", "id": str(s.id),
            "tracking_number": s.tracking_number, "status": s.status,
            "content": f"Shipment {s.tracking_number or ''} - {s.status}",
            "carrier": s.carrier,
            "timestamp": s.created_at.isoformat(),
        })

    # Sort by timestamp descending
    timeline.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"contact_id": str(contact_id), "events": timeline[:limit]}
