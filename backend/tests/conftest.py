"""Shared test fixtures for pytest.

The test suite expects the schema to already exist — apply migrations with
`alembic upgrade head` before running. We intentionally do NOT create or
drop tables here: under the runtime app_user role we lack ownership, and
relying on ALembic keeps dev/test/prod schema in lock-step.

Each test's own DB writes live in their own transactions (the API's own
`get_db` wraps each request in begin/commit/rollback). If you need strict
isolation between tests, generate unique identifiers (emails, phones, etc.)
inside the test.
"""

import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.main import app

settings = get_settings()


# Per-test engines: asyncpg connections are bound to the event loop that
# created them. pytest-asyncio spins up a fresh loop per test, so a module-
# level engine will fail on the second test with "attached to a different
# loop". Building the engine inside the fixture (function scope) sidesteps
# that entirely.
def _make_engine(url: str):
    return create_async_engine(url, echo=False, poolclass=NullPool)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Per-test session under the runtime (app_user) role.

    For assertions that need to peek into RLS-protected tables without a
    tenant context, use `db_session_privileged`.
    """
    engine = _make_engine(settings.database_url)
    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    try:
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session_privileged() -> AsyncGenerator[AsyncSession, None]:
    """Session under the schema-owner role, for cross-tenant assertions.

    Reads MIGRATION_DATABASE_URL from the environment when available, which
    docker-compose provides for the api container. Falls back to the runtime
    URL (which works in dev where app_user is actually a superuser stand-in
    in the test environment).
    """
    url = os.getenv("MIGRATION_DATABASE_URL") or settings.database_url
    engine = _make_engine(url)
    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    try:
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
async def _reset_mutable_tables() -> AsyncGenerator[None, None]:
    """TRUNCATE data tables at session start under the schema-owner role.

    Tests expect a blank canvas but we can't DROP tables (app_user lacks
    ownership) and shouldn't (Alembic owns the schema). Instead we truncate
    every tenant-scoped data table using a privileged connection. This
    keeps migrated schema in place while giving each test suite a clean
    database, including auth rows with fixed emails in the pre-existing
    tests.

    Runs exactly once per pytest session.
    """
    url = os.getenv("MIGRATION_DATABASE_URL") or settings.database_url
    engine = _make_engine(url)
    try:
        async with engine.begin() as conn:
            from sqlalchemy import text

            # Order doesn't matter with TRUNCATE ... CASCADE; we list the
            # tables that accumulate test fixtures.
            await conn.execute(
                text(
                    "TRUNCATE TABLE "
                    "audit_logs, user_roles, api_keys, "
                    "contact_tags, custom_field_values, deal_activities, "
                    "automation_logs, automation_actions, automations, "
                    "message_templates, "
                    "messages, conversations, deals, pipeline_stages, "
                    "pipelines, contacts, tags, custom_fields, "
                    "campaign_recipients, campaigns, landing_pages, "
                    "glossary_terms, "
                    "shipments, subscriptions, invoices, payments, "
                    "users, companies, roles "
                    "RESTART IDENTITY CASCADE"
                )
            )
    except Exception:
        # If the privileged engine can't connect, tests will still run;
        # existing data may cause conflicts on tests with fixed identifiers.
        pass
    finally:
        await engine.dispose()
    yield


@pytest.fixture(autouse=True)
async def _reset_rate_limit_buckets() -> AsyncGenerator[None, None]:
    """Flush the rate-limit keys from Redis before each test.

    Without this, multiple registers within a single test file exhaust the
    per-IP login/register bucket and later tests see 429s from the
    RateLimitMiddleware (the TestClient reports a single client IP for every
    request). Flushing only the `rl:*` keyspace leaves the rest of Redis
    intact so other in-flight work (celery queues, WS pub/sub) isn't touched.
    """
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        async for key in redis.scan_iter(match="rl:*", count=500):
            await redis.delete(key)
    except Exception:
        pass
    yield


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client. Each request goes through the real get_db."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
