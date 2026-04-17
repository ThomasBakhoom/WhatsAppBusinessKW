"""Data export API - CSV export for contacts, conversations, deals."""

import csv
import io
from uuid import UUID
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from app.dependencies import AuthUser, TenantDbSession
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.pipeline import Deal

router = APIRouter()


@router.get("/contacts")
async def export_contacts(db: TenantDbSession, user: AuthUser):
    """Export all contacts as CSV."""
    result = await db.execute(
        select(Contact).where(
            Contact.company_id == user.company_id, Contact.deleted_at.is_(None)
        ).order_by(Contact.created_at)
    )
    contacts = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["phone", "email", "first_name", "last_name", "status", "source", "lead_score", "opt_in_whatsapp", "created_at"])
    for c in contacts:
        writer.writerow([c.phone, c.email or "", c.first_name, c.last_name, c.status, c.source, c.lead_score, c.opt_in_whatsapp, c.created_at.isoformat()])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=contacts_export.csv"},
    )


@router.get("/conversations")
async def export_conversations(db: TenantDbSession, user: AuthUser):
    """Export conversations summary as CSV."""
    result = await db.execute(
        select(Conversation).where(Conversation.company_id == user.company_id)
        .order_by(Conversation.created_at.desc()).limit(5000)
    )
    convs = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "contact_id", "status", "channel", "unread_count", "last_message_preview", "last_message_at", "created_at"])
    for c in convs:
        writer.writerow([str(c.id), str(c.contact_id), c.status, c.channel, c.unread_count, c.last_message_preview or "", c.last_message_at.isoformat() if c.last_message_at else "", c.created_at.isoformat()])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=conversations_export.csv"},
    )


@router.get("/deals")
async def export_deals(db: TenantDbSession, user: AuthUser):
    """Export deals as CSV."""
    result = await db.execute(
        select(Deal).where(
            Deal.company_id == user.company_id, Deal.deleted_at.is_(None)
        ).order_by(Deal.created_at.desc())
    )
    deals = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "title", "value", "currency", "status", "pipeline_id", "stage_id", "contact_id", "created_at"])
    for d in deals:
        writer.writerow([str(d.id), d.title, str(d.value), d.currency, d.status, str(d.pipeline_id), str(d.stage_id) if d.stage_id else "", str(d.contact_id) if d.contact_id else "", d.created_at.isoformat()])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=deals_export.csv"},
    )
