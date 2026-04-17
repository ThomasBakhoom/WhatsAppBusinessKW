"""Celery tasks for campaign execution.

Dispatches each recipient as an individual WhatsApp message via the same
`send_whatsapp_message` task used by the inbox. This means:
  * Each message gets its own delivery-status webhook tracking.
  * Failures are isolated per-recipient (one bad phone doesn't kill the run).
  * The Cloud API rate limit (~80/sec) is respected by chunking + sleep.

If WhatsApp is not configured for the company (no phone_number_id), the
campaign immediately moves to "failed" and no messages are attempted.
"""

from __future__ import annotations

import asyncio

import structlog
from app.tasks.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    name="app.tasks.campaigns.execute_campaign",
    bind=True, queue="messaging", max_retries=0,
)
def execute_campaign(self, campaign_id: str, company_id: str):
    """Process all recipients in a campaign."""
    return asyncio.run(_async_execute(campaign_id, company_id))


async def _async_execute(campaign_id: str, company_id: str) -> dict:
    from uuid import UUID
    from datetime import datetime, timezone
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal, tenant_session
    from app.models.campaign import Campaign, CampaignRecipient
    from app.models.company import Company

    company_uuid = UUID(company_id)
    campaign_uuid = UUID(campaign_id)
    sent = failed = 0
    current_status = "sending"

    # ── 1. Pre-flight: check company has WhatsApp configured ──────────
    async with AsyncSessionLocal() as bootstrap:
        co = await bootstrap.execute(
            select(Company).where(Company.id == company_uuid)
        )
        company = co.scalar_one_or_none()
    has_whatsapp = bool(company and company.whatsapp_phone_number_id)

    # ── 2. Load campaign + recipient ids ──────────────────────────────
    async with tenant_session(company_uuid) as db:
        result = await db.execute(
            select(Campaign).where(Campaign.id == campaign_uuid)
        )
        campaign = result.scalar_one_or_none()
        if not campaign or campaign.status != "sending":
            return {"status": "skipped"}

        if not has_whatsapp:
            campaign.status = "failed"
            campaign.completed_at = datetime.now(timezone.utc)
            logger.warning("campaign_no_whatsapp", campaign_id=campaign_id)
            return {"status": "failed", "error": "WhatsApp not configured for company"}

        # Load message content from campaign
        msg_type = campaign.message_type  # "template" or "text"
        template_name = campaign.template_name
        template_language = campaign.template_language
        message_body = campaign.message_body
        media_url = campaign.media_url

        result = await db.execute(
            select(CampaignRecipient.id, CampaignRecipient.phone).where(
                CampaignRecipient.campaign_id == campaign_uuid,
                CampaignRecipient.status == "pending",
            ).limit(10000)
        )
        recipients = [(row[0], row[1]) for row in result.all()]

    if not recipients:
        return {"status": "no_recipients"}

    # ── 3. Send in chunks ─────────────────────────────────────────────
    chunk_size = 80
    for chunk_start in range(0, len(recipients), chunk_size):
        chunk = recipients[chunk_start:chunk_start + chunk_size]

        async with tenant_session(company_uuid) as db:
            # Re-check pause/cancel
            camp_check = await db.execute(
                select(Campaign.status).where(Campaign.id == campaign_uuid)
            )
            current_status = camp_check.scalar_one()
            if current_status != "sending":
                logger.info("campaign_paused", campaign_id=campaign_id)
                break

            now = datetime.now(timezone.utc)
            for rec_id, phone in chunk:
                rec_result = await db.execute(
                    select(CampaignRecipient).where(CampaignRecipient.id == rec_id)
                )
                rec = rec_result.scalar_one_or_none()
                if rec is None:
                    continue
                try:
                    # Dispatch the actual WhatsApp send via the messaging task.
                    # This creates a Message row, calls Cloud API, and tracks
                    # delivery via webhooks — same as sending from the inbox.
                    from app.tasks.messaging_tasks import send_whatsapp_message

                    send_whatsapp_message.delay(
                        message_id="",  # no pre-created message row for campaigns
                        company_id=company_id,
                        to=phone,
                        message_type=msg_type,
                        content=message_body,
                        media_url=media_url,
                        template_name=template_name if msg_type == "template" else None,
                        template_language=template_language if msg_type == "template" else None,
                    )
                    rec.status = "sent"
                    rec.sent_at = now
                    sent += 1
                except Exception as e:
                    rec.status = "failed"
                    rec.error_message = str(e)[:500]
                    failed += 1
                    logger.warning(
                        "campaign_send_failed",
                        campaign_id=campaign_id,
                        phone=phone,
                        error=str(e),
                    )

        # Pace between chunks
        if current_status == "sending":
            await asyncio.sleep(1)

    # ── 4. Final stats ────────────────────────────────────────────────
    async with tenant_session(company_uuid) as db:
        result = await db.execute(
            select(Campaign).where(Campaign.id == campaign_uuid)
        )
        campaign = result.scalar_one_or_none()
        if campaign:
            campaign.sent_count = sent
            campaign.failed_count = failed
            campaign.delivered_count = sent  # delivery confirmation via webhook
            if current_status == "sending":
                campaign.status = "sent"
                campaign.completed_at = datetime.now(timezone.utc)

    logger.info(
        "campaign_complete",
        campaign_id=campaign_id,
        sent=sent,
        failed=failed,
        has_whatsapp=has_whatsapp,
    )
    return {"status": "sent", "sent": sent, "failed": failed}
