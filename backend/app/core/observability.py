"""Observability hooks: Sentry initialization, log/transport plumbing.

Kept tiny on purpose. Read settings, decide whether to enable, and call
`sentry_sdk.init` once at startup. If the SDK is not installed (e.g. in a
slim test environment) we no-op so the app still boots.
"""

from __future__ import annotations

import structlog

from app.config import Settings

logger = structlog.get_logger()


def init_sentry(settings: Settings) -> bool:
    """Initialize Sentry if SENTRY_DSN is configured. Returns True if enabled."""
    if not settings.sentry_dsn:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.asyncio import AsyncioIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        logger.warning("sentry_sdk_not_installed_but_dsn_set")
        return False

    # Sample rates: full error capture in non-prod for visibility; in prod
    # we capture everything but keep traces sampled to control cost.
    traces_sample_rate = 0.1 if settings.is_production else 1.0
    profiles_sample_rate = 0.1 if settings.is_production else 0.0

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        release=f"{settings.app_name}@{settings.app_version}",
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        send_default_pii=False,  # never send Authorization header / cookies
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            AsyncioIntegration(),
        ],
        # Avoid noisy 4xx capture; keep 5xx and uncaught exceptions.
        before_send=_drop_4xx,
    )
    logger.info(
        "sentry_initialized",
        environment=settings.app_env,
        traces_sample_rate=traces_sample_rate,
    )
    return True


def _drop_4xx(event, hint):  # pragma: no cover - thin filter
    """Skip Sentry events triggered by HTTPException with status < 500."""
    exc_info = hint.get("exc_info") if hint else None
    if not exc_info:
        return event
    exc = exc_info[1]
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int) and 400 <= status_code < 500:
        return None
    return event
