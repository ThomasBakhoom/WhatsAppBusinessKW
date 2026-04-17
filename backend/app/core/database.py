from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
)

# For testing: use NullPool
test_engine = create_async_engine(
    settings.database_url,
    echo=False,
    poolclass=NullPool,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Alias for use outside of FastAPI dependency injection (e.g., Celery tasks)
async_session_factory = AsyncSessionLocal


async def set_tenant_context(session: AsyncSession, company_id: UUID) -> None:
    """
    Set the RLS tenant context (`app.current_tenant`) on a session.

    Must be called inside an open transaction (SET LOCAL only persists for the
    current transaction). For raw `AsyncSessionLocal()` usage, wrap your work
    in `async with session.begin():` so the GUC stays in effect.

    The company_id comes from a validated UUID (JWT payload, FK lookup, or
    webhook -> companies row), so f-string interpolation is safe; asyncpg
    refuses parameter binding inside SET LOCAL.
    """
    tenant_id = str(company_id)
    await session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))


@asynccontextmanager
async def tenant_session(company_id: UUID) -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager that yields a session with tenant context set.

    Use from Celery tasks, webhook handlers, and any other code outside of
    FastAPI dependency injection. Commits on success, rolls back on error.

        async with tenant_session(company_id) as db:
            await db.execute(...)
    """
    async with AsyncSessionLocal() as session:
        try:
            async with session.begin():
                await set_tenant_context(session, company_id)
                yield session
        except Exception:
            # session.begin() will have already rolled back on exception
            raise
        finally:
            await session.close()


# Backwards-compat alias for older imports.
async def get_db_with_tenant(
    session: AsyncSession, company_id: UUID
) -> AsyncSession:
    """Deprecated: prefer `set_tenant_context` or `tenant_session`."""
    await set_tenant_context(session, company_id)
    return session
