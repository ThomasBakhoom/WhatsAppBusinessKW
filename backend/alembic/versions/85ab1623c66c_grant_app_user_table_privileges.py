"""grant_app_user_table_privileges

Grants the runtime `app_user` role the privileges it needs to run the API
under a non-bypass-RLS connection.

WHY THIS MATTERS:
The database superuser (`kwgrowth` in dev) bypasses Row-Level Security even
when policies are FORCEd. The RLS migration (f56baac2d30e) created tenant
isolation policies, but they only take effect when the connection is made
under a role that does NOT have BYPASSRLS or SUPERUSER. The intended runtime
role is `app_user`, created in docker/postgres/init.sql.

This migration grants `app_user` the table/sequence privileges required for
the API to operate, but does NOT change the runtime DATABASE_URL. Switching
the API to connect as `app_user` is a separate, audit-heavy step because:

  - The register flow creates a Company *before* a tenant context exists,
    so it must SET LOCAL app.current_tenant after the company is created
    and before any RLS-protected INSERT.
  - Background workers (Celery) need the same treatment.
  - Any endpoint using `DbSession` instead of `TenantDbSession` will start
    failing if it touches a tenant-scoped table.

To switch over (after auditing the above):
  1. In docker/.env.docker (and your secret manager), set:
       APP_USER_PASSWORD=<strong-secret>
       DATABASE_URL=postgresql+asyncpg://app_user:<password>@db:5432/kwgrowth
  2. ALTER ROLE app_user PASSWORD '<strong-secret>';
  3. Restart the API.

Revision ID: 85ab1623c66c
Revises: f56baac2d30e
Create Date: 2026-04-15
"""
from typing import Sequence, Union

from alembic import op


revision: str = "85ab1623c66c"
down_revision: Union[str, None] = "f56baac2d30e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Make sure the role exists (init.sql creates it, but a freshly-built
    # external DB may not have it).
    bind.exec_driver_sql(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
                CREATE ROLE app_user LOGIN PASSWORD 'change-me-in-prod';
            END IF;
        END $$;
        """
    )

    # Schema usage so the role can resolve table names.
    bind.exec_driver_sql("GRANT USAGE ON SCHEMA public TO app_user")

    # Full DML on every existing table. Future tables created in this schema
    # are already covered by the ALTER DEFAULT PRIVILEGES set in init.sql.
    bind.exec_driver_sql(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user"
    )
    bind.exec_driver_sql(
        "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user"
    )

    # Default privileges so future migrations don't need to re-grant.
    bind.exec_driver_sql(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user"
    )
    bind.exec_driver_sql(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT USAGE, SELECT ON SEQUENCES TO app_user"
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        "REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM app_user"
    )
    bind.exec_driver_sql(
        "REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public FROM app_user"
    )
    bind.exec_driver_sql(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM app_user"
    )
    bind.exec_driver_sql(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "REVOKE USAGE, SELECT ON SEQUENCES FROM app_user"
    )
    bind.exec_driver_sql("REVOKE USAGE ON SCHEMA public FROM app_user")
