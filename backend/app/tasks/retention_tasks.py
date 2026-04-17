"""Data retention tasks.

CITRA Kuwait compliance requires us to honor the retention policies we
advertise in `citra_compliance.py`. The rules we enforce here:

  * Soft-deleted contacts older than `data_retention_days` (default 365)
    are hard-deleted from the database. Per-company override via
    `companies.settings.data_retention_days`.
  * Closed conversations older than `conversation_retention_days` (default
    365) are hard-deleted along with their messages. Per-company override
    via `companies.settings.conversation_retention_days`.
  * Audit logs are NEVER deleted (compliance says "immutable" → 5 years).
    This task will not touch them even if misconfigured.
  * Payments/invoices are NEVER deleted (Kuwait commercial law: 7 years).

Execution model: a single Celery beat tick runs `purge_retention` daily,
which enumerates companies (non-RLS) then runs the purge per-tenant inside
`tenant_session(company_id)` so RLS is respected and one tenant's failure
doesn't poison the others.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import structlog

from app.tasks.celery_app import celery_app

logger = structlog.get_logger()


DEFAULT_CONTACT_RETENTION_DAYS = 365
DEFAULT_CONVERSATION_RETENTION_DAYS = 365
DEFAULT_AI_CONTEXT_RETENTION_DAYS = 90
DEFAULT_ANALYTICS_RAW_RETENTION_DAYS = 730  # 24 months


@celery_app.task(
    name="app.tasks.retention.purge_retention",
    queue="default",
    max_retries=0,
)
def purge_retention_task() -> dict:
    """Celery entrypoint. Runs `purge_retention` and reports totals."""
    try:
        return asyncio.run(_purge_retention())
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("retention_purge_failed", error=str(exc))
        return {"status": "error", "error": str(exc)}


async def _purge_retention() -> dict:
    from uuid import UUID

    from sqlalchemy import delete, select

    from app.core.database import AsyncSessionLocal, tenant_session
    from app.models.ai_context import AIConversationContext
    from app.models.company import Company
    from app.models.contact import Contact
    from app.models.conversation import Conversation
    from app.models.message import Message

    # Enumerate tenants under the (non-RLS) companies table.
    async with AsyncSessionLocal() as bootstrap:
        result = await bootstrap.execute(
            select(Company.id, Company.settings, Company.name)
        )
        tenants = [(row[0], row[1] or {}, row[2]) for row in result.all()]

    totals = {
        "tenants_processed": 0,
        "tenants_failed": 0,
        "contacts_purged": 0,
        "conversations_purged": 0,
        "messages_purged": 0,
        "ai_contexts_purged": 0,
    }
    now = datetime.now(timezone.utc)

    for company_id, company_settings, company_name in tenants:
        contact_days = int(
            company_settings.get("data_retention_days")
            or DEFAULT_CONTACT_RETENTION_DAYS
        )
        conv_days = int(
            company_settings.get("conversation_retention_days")
            or DEFAULT_CONVERSATION_RETENTION_DAYS
        )
        ai_days = int(
            company_settings.get("ai_context_retention_days")
            or DEFAULT_AI_CONTEXT_RETENTION_DAYS
        )
        contact_cutoff = now - timedelta(days=contact_days)
        conv_cutoff = now - timedelta(days=conv_days)
        ai_cutoff = now - timedelta(days=ai_days)

        try:
            async with tenant_session(UUID(str(company_id))) as db:
                # 1. Hard-delete soft-deleted contacts past retention.
                contact_q = delete(Contact).where(
                    Contact.deleted_at.is_not(None),
                    Contact.deleted_at < contact_cutoff,
                )
                result = await db.execute(contact_q)
                totals["contacts_purged"] += result.rowcount or 0

                # 2. Hard-delete closed conversations + their messages past
                #    retention. Delete messages first to satisfy FK ordering,
                #    then the conversation shell.
                conv_ids_q = await db.execute(
                    select(Conversation.id).where(
                        Conversation.status == "closed",
                        Conversation.last_message_at.is_not(None),
                        Conversation.last_message_at < conv_cutoff,
                    )
                )
                conv_ids = [row[0] for row in conv_ids_q.all()]

                if conv_ids:
                    msg_result = await db.execute(
                        delete(Message).where(Message.conversation_id.in_(conv_ids))
                    )
                    totals["messages_purged"] += msg_result.rowcount or 0

                    conv_result = await db.execute(
                        delete(Conversation).where(Conversation.id.in_(conv_ids))
                    )
                    totals["conversations_purged"] += conv_result.rowcount or 0

                # 3. Hard-delete AI conversation contexts older than retention.
                #    These are analysis artifacts (dialect, intent, sentiment)
                #    attached to conversations. Per CITRA policy: 90 days default.
                #    The FK to conversations is CASCADE, so if the conversation
                #    was already deleted above the context goes with it; this
                #    catches contexts whose parent conversation is still open
                #    but the analysis is stale.
                ai_q = delete(AIConversationContext).where(
                    AIConversationContext.updated_at < ai_cutoff,
                )
                ai_result = await db.execute(ai_q)
                totals["ai_contexts_purged"] += ai_result.rowcount or 0

                # 4. Audit: record that we did this (under the tenant context).
                from app.models.audit import AuditLog

                db.add(
                    AuditLog(
                        company_id=company_id,
                        action="retention.purge",
                        description=(
                            f"Retention purge: "
                            f"{totals['contacts_purged']} contacts, "
                            f"{totals['conversations_purged']} conversations, "
                            f"{totals['messages_purged']} messages, "
                            f"{totals['ai_contexts_purged']} AI contexts"
                        ),
                        resource_type="company",
                        resource_id=str(company_id),
                        changes={
                            "contact_retention_days": contact_days,
                            "conversation_retention_days": conv_days,
                            "ai_context_retention_days": ai_days,
                        },
                    )
                )

            totals["tenants_processed"] += 1
            logger.info(
                "retention_purge_tenant_done",
                company_id=str(company_id),
                company_name=company_name,
                contact_retention_days=contact_days,
                conversation_retention_days=conv_days,
            )
        except Exception as exc:
            totals["tenants_failed"] += 1
            logger.warning(
                "retention_purge_tenant_failed",
                company_id=str(company_id),
                company_name=company_name,
                error=str(exc),
            )

    logger.info("retention_purge_complete", **totals)
    return {"status": "ok", **totals}
