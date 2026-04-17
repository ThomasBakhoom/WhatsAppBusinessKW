"""Periodic/beat tasks referenced in celery_app.py beat_schedule."""

import asyncio

import structlog
from app.tasks.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="app.tasks.analytics.aggregate_daily", queue="analytics")
def aggregate_daily():
    """Aggregate daily analytics. Runs at 2 AM."""
    logger.info("aggregate_daily_started")
    # Future: compute daily rollups of message counts, conversation stats, etc.
    return {"status": "ok"}


@celery_app.task(name="app.tasks.payments.check_renewals", queue="default")
def check_renewals():
    """Check for subscriptions due for renewal. Runs hourly."""
    try:
        return asyncio.run(_async_check_renewals())
    except Exception as e:
        logger.error("check_renewals_failed", error=str(e))
        return {"status": "error", "error": str(e)}


async def _async_check_renewals() -> dict:
    """Check expired subscriptions across ALL tenants.

    `subscriptions` is RLS-protected, so we can't scan it cross-tenant from a
    non-bypass role. Strategy: enumerate companies (no RLS), then run the
    expiry check inside each company's tenant context.
    """
    from datetime import datetime, timezone
    from uuid import UUID
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal, tenant_session
    from app.models.company import Company
    from app.models.payment import Subscription

    now = datetime.now(timezone.utc)
    total_past_due = 0

    # Enumerate tenants from the (non-RLS) companies table.
    async with AsyncSessionLocal() as bootstrap:
        result = await bootstrap.execute(select(Company.id))
        company_ids: list[UUID] = [row[0] for row in result.all()]

    for company_id in company_ids:
        try:
            async with tenant_session(company_id) as db:
                result = await db.execute(
                    select(Subscription).where(
                        Subscription.status == "active",
                        Subscription.current_period_end <= now,
                        Subscription.cancel_at_period_end == False,  # noqa: E712
                    )
                )
                for sub in result.scalars().all():
                    sub.status = "past_due"
                    total_past_due += 1
                    logger.info(
                        "subscription_past_due",
                        subscription_id=str(sub.id),
                        company_id=str(company_id),
                    )
        except Exception as exc:
            # Don't let one bad tenant break the whole sweep.
            logger.warning(
                "renewal_check_failed_for_tenant",
                company_id=str(company_id),
                error=str(exc),
            )

    return {"status": "ok", "past_due": total_past_due}


@celery_app.task(name="app.tasks.webhooks.retry_failed", queue="webhooks")
def retry_failed():
    """Retry failed webhook deliveries. Runs every 5 minutes."""
    logger.info("retry_failed_webhooks")
    # Future: query failed outbound webhooks and retry
    return {"status": "ok"}


@celery_app.task(name="app.tasks.messaging.sync_templates", queue="messaging")
def sync_templates():
    """Sync WhatsApp message templates from Cloud API. Runs every 6 hours."""
    logger.info("sync_templates_started")
    # Future: call WhatsApp Cloud API to fetch approved templates
    return {"status": "ok"}


@celery_app.task(name="app.tasks.auth.cleanup_sessions", queue="default")
def cleanup_sessions():
    """Clean up expired sessions/tokens. Runs daily at 3 AM."""
    logger.info("cleanup_sessions_started")
    # Future: remove expired refresh tokens from DB
    return {"status": "ok"}
