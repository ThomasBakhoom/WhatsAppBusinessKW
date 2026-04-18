"""Alembic environment configuration for async SQLAlchemy."""

import asyncio
import os
import sys
from pathlib import Path
from logging.config import fileConfig

# Ensure the backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import all models so Alembic can detect them
from app.models.base import Base
from app.models import *  # noqa: F401, F403
from app.config import _normalize_postgres_url, get_settings

config = context.config
settings = get_settings()

# Migrations must run as the schema OWNER (not the runtime app_user, which
# is a non-superuser and lacks CREATE/ALTER privileges). When
# MIGRATION_DATABASE_URL is set in the environment, prefer it over the
# runtime DATABASE_URL. The URL is also normalized so a plain
# `postgresql://...` from a managed provider (Railway, Render, Heroku)
# gets the +asyncpg driver appended automatically.
migration_url = _normalize_postgres_url(
    os.getenv("MIGRATION_DATABASE_URL") or settings.database_url
)
config.set_main_option("sqlalchemy.url", migration_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL without connecting)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
