"""Celery application factory and configuration."""

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "kwgrowth",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,

    # Queue routing
    task_default_queue="default",
    task_queues={
        "default": {},
        "messaging": {},
        "automations": {},
        "webhooks": {},
        "analytics": {},
        "imports": {},
        "shipping": {},
        "ai": {},
    },

    # Rate limiting
    task_annotations={
        "app.tasks.messaging.*": {"rate_limit": "80/s"},
        "app.tasks.webhooks.*": {"rate_limit": "50/s"},
    },

    # Retry policy
    task_default_retry_delay=60,
    task_max_retries=3,

    # Beat schedule (periodic tasks)
    beat_schedule={
        "aggregate-daily-analytics": {
            "task": "app.tasks.analytics.aggregate_daily",
            "schedule": crontab(hour=2, minute=0),
        },
        "check-subscription-renewals": {
            "task": "app.tasks.payments.check_renewals",
            "schedule": crontab(minute=0),  # Every hour
        },
        "retry-failed-webhooks": {
            "task": "app.tasks.webhooks.retry_failed",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        },
        "sync-whatsapp-templates": {
            "task": "app.tasks.messaging.sync_templates",
            "schedule": crontab(hour="*/6", minute=0),  # Every 6 hours
        },
        "cleanup-expired-sessions": {
            "task": "app.tasks.auth.cleanup_sessions",
            "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
        },
        "purge-retention": {
            "task": "app.tasks.retention.purge_retention",
            "schedule": crontab(hour=4, minute=17),  # Daily at 04:17 UTC
            # Off-the-hour on purpose so retention scans don't line up with
            # midnight reports.
        },
    },
)

# Explicitly register task modules
celery_app.autodiscover_tasks([
    "app.tasks.import_tasks",
    "app.tasks.messaging_tasks",
    "app.tasks.automation_tasks",
    "app.tasks.ai_tasks",
    "app.tasks.shipping_tasks",
    "app.tasks.periodic_tasks",
    "app.tasks.campaign_tasks",
    "app.tasks.retention_tasks",
])
