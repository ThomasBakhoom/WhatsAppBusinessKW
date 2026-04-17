"""Instagram webhook endpoints - comments, DMs, and story mentions."""

from uuid import UUID

import structlog
from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import text

from app.config import get_settings
from app.core.database import AsyncSessionLocal, tenant_session
from app.services.channels.instagram_comments import InstagramCommentCapture

logger = structlog.get_logger()
settings = get_settings()

router = APIRouter()


@router.get("/instagram")
async def verify_instagram_webhook(
    mode: str = Query(alias="hub.mode", default=""),
    token: str = Query(alias="hub.verify_token", default=""),
    challenge: str = Query(alias="hub.challenge", default=""),
):
    """Instagram webhook verification (same pattern as WhatsApp - Meta platform)."""
    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Forbidden", status_code=403)


def _iter_entry_page_ids(payload: dict):
    """Yield (page_id, entry_dict) for each entry in the Meta webhook payload.

    Each entry's top-level `id` is the Page ID on which the event occurred.
    We split the payload at this level so every change is processed under
    the correct tenant context — ONE page belongs to exactly ONE company.
    """
    for entry in payload.get("entry", []):
        page_id = entry.get("id")
        if page_id:
            yield str(page_id), entry


async def _resolve_channel(
    page_id: str,
) -> tuple[UUID, UUID, str] | None:
    """Resolve (company_id, channel_id, access_token) for a page id.

    Calls the SECURITY DEFINER function `resolve_instagram_channel` (see
    migration 1cefbd1e74ea) which is the ONLY cross-tenant read we allow
    on the channels table — necessary because webhooks arrive without
    tenant context.
    """
    async with AsyncSessionLocal() as bootstrap:
        try:
            result = await bootstrap.execute(
                text("SELECT * FROM public.resolve_instagram_channel(:pid)"),
                {"pid": page_id},
            )
            row = result.first()
        except Exception as exc:
            logger.warning(
                "instagram_channel_resolver_failed",
                page_id=page_id,
                error=str(exc),
            )
            return None

    if row is None:
        return None
    company_id, channel_id, access_token = row
    return UUID(str(company_id)), UUID(str(channel_id)), access_token or ""


@router.post("/instagram")
async def receive_instagram_webhook(request: Request):
    """Handle Instagram webhook events - comments, DMs, mentions.

    For each `entry` in the payload, resolves the owning company via the
    Page ID (`entry.id`), then processes that entry's events inside the
    correct tenant context. If no channel exists for a page (webhook for
    a company we don't know about), the entry is skipped — NOT routed to
    an arbitrary tenant, which was the old bug.
    """
    payload = await request.json()
    logger.info(
        "instagram_webhook_received",
        entry_count=len(payload.get("entry", [])),
    )

    processed = 0
    unmatched = 0

    for page_id, entry in _iter_entry_page_ids(payload):
        resolved = await _resolve_channel(page_id)
        if resolved is None:
            unmatched += 1
            logger.info(
                "instagram_webhook_unknown_page",
                page_id=page_id,
                hint="Connect this Instagram Page inside the app to receive its events.",
            )
            continue

        company_id, _channel_id, access_token = resolved

        async with tenant_session(company_id) as db:
            capture = InstagramCommentCapture(db, company_id, access_token)
            # Feed the capture a single-entry payload so it parses only events
            # belonging to THIS company.
            single_payload = {"entry": [entry]}
            leads = capture.parse_comment_webhook(single_payload)
            for lead in leads:
                result = await capture.process_comment_lead(lead)
                logger.info(
                    "instagram_comment_lead_processed",
                    company_id=str(company_id),
                    ig_user=lead["username"],
                    is_new=result["is_new"],
                    actions=result["actions"],
                )
            processed += 1

    return {
        "status": "ok",
        "processed_entries": processed,
        "unmatched_entries": unmatched,
    }
