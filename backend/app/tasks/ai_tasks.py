"""Celery tasks for AI analysis."""

import asyncio

import structlog
from app.tasks.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    name="app.tasks.ai.analyze_message",
    bind=True,
    queue="ai",
    max_retries=1,
)
def analyze_message_task(
    self,
    company_id: str,
    conversation_id: str,
    message_content: str,
    direction: str = "inbound",
):
    """Analyze a message using AI asynchronously."""
    try:
        return asyncio.run(
            _async_analyze(company_id, conversation_id, message_content, direction)
        )
    except Exception as exc:
        logger.error("ai_analysis_task_failed", error=str(exc))
        raise self.retry(exc=exc)


async def _async_analyze(
    company_id: str,
    conversation_id: str,
    message_content: str,
    direction: str,
) -> dict:
    from uuid import UUID
    from app.core.database import tenant_session

    company_uuid = UUID(company_id)
    async with tenant_session(company_uuid) as db:
        from app.services.ai.dialect_engine import DialectEngine
        ai = DialectEngine(db, company_uuid)
        return await ai.analyze_message(
            UUID(conversation_id), message_content, direction
        )
