"""Celery tasks for automation execution."""

import asyncio

import structlog
from app.tasks.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(
    name="app.tasks.automations.evaluate_event",
    bind=True,
    queue="automations",
    max_retries=1,
)
def evaluate_automation_event(
    self,
    company_id: str,
    event_type: str,
    event_data: dict,
):
    """Evaluate automations for an event asynchronously."""
    try:
        result = asyncio.run(
            _async_evaluate(company_id, event_type, event_data)
        )
        return result
    except Exception as exc:
        logger.error("automation_eval_failed", error=str(exc))
        raise self.retry(exc=exc)


async def _async_evaluate(
    company_id: str, event_type: str, event_data: dict
) -> dict:
    from uuid import UUID
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.config import get_settings

    settings = get_settings()

    # Create a fresh engine for this task (avoids event loop conflicts)
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_factory() as db:
            from app.services.automation_service import AutomationService
            svc = AutomationService(db, UUID(company_id))
            executed = await svc.evaluate_event(event_type, event_data)
            await db.commit()

        return {
            "company_id": company_id,
            "event_type": event_type,
            "automations_executed": len(executed),
            "automation_ids": [str(aid) for aid in executed],
        }
    finally:
        await engine.dispose()
