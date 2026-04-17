"""enable_rls_on_tenant_tables

Enables PostgreSQL Row-Level Security on every multi-tenant table (i.e. every
table that carries a `company_id` column).

Two policies per table:
  - tenant_isolation_policy: SELECT/UPDATE/DELETE filtered by the
    `app.current_tenant` GUC, which the API sets per-request via
    `SET LOCAL app.current_tenant = '<company_uuid>'` (see
    app/dependencies.py::get_tenant_db and app/core/database.py).
  - tenant_insert_policy: INSERTs must carry the matching company_id.

`FORCE ROW LEVEL SECURITY` is enabled so the table owner is also subject to
the policies — without this, queries run as the schema owner bypass RLS.

The `enable_rls()` helper function is created in docker/postgres/init.sql.
This migration also re-creates that helper (idempotently) so that fresh
databases provisioned outside the Docker init flow still get it.

Revision ID: f56baac2d30e
Revises: c1d2baf5e47d
Create Date: 2026-04-15 08:32:22.801658
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f56baac2d30e"
down_revision: Union[str, None] = "c1d2baf5e47d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables that carry company_id and therefore need tenant isolation.
# Sourced from `SELECT table_name FROM information_schema.columns WHERE
# column_name='company_id'` after the initial schema migration.
TENANT_TABLES: tuple[str, ...] = (
    "ai_conversation_contexts",
    "api_keys",
    "audit_logs",
    "automation_logs",
    "automations",
    "campaigns",
    "channels",
    "chatbot_flows",
    "contacts",
    "conversations",
    "custom_fields",
    "deals",
    "glossary_terms",
    "invoices",
    "landing_pages",
    "message_templates",
    "messages",
    "payments",
    "pipelines",
    "product_categories",
    "products",
    "routing_decisions",
    "shipments",
    "shipping_providers",
    "subscriptions",
    "survey_responses",
    "surveys",
    "tags",
    "users",
    "web_chat_widgets",
)


# Idempotent re-creation of the enable_rls helper. Safe to run repeatedly.
ENABLE_RLS_FN = """
CREATE OR REPLACE FUNCTION enable_rls(table_name TEXT) RETURNS void AS $$
BEGIN
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', table_name);

    -- Drop any previous policies first so this is idempotent.
    EXECUTE format('DROP POLICY IF EXISTS tenant_isolation_policy ON %I', table_name);
    EXECUTE format('DROP POLICY IF EXISTS tenant_insert_policy ON %I', table_name);

    -- SELECT/UPDATE/DELETE policy: only rows for the current tenant are visible.
    -- Using current_setting(..., true) so a missing GUC raises a clear error
    -- rather than returning NULL (which would silently match no rows).
    EXECUTE format(
        'CREATE POLICY tenant_isolation_policy ON %I
         FOR ALL
         USING (company_id = current_setting(''app.current_tenant'')::uuid)',
        table_name
    );

    -- INSERT policy: the inserted row must belong to the current tenant.
    EXECUTE format(
        'CREATE POLICY tenant_insert_policy ON %I
         FOR INSERT
         WITH CHECK (company_id = current_setting(''app.current_tenant'')::uuid)',
        table_name
    );
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    bind = op.get_bind()
    # Make sure the helper exists (it normally comes from init.sql, but a fresh
    # DB created via plain `createdb` won't have it).
    bind.exec_driver_sql(ENABLE_RLS_FN)

    for table in TENANT_TABLES:
        bind.exec_driver_sql(f"SELECT enable_rls('{table}')")


def downgrade() -> None:
    bind = op.get_bind()
    for table in TENANT_TABLES:
        # Drop policies first, then disable RLS.
        bind.exec_driver_sql(
            f'DROP POLICY IF EXISTS tenant_isolation_policy ON "{table}"'
        )
        bind.exec_driver_sql(
            f'DROP POLICY IF EXISTS tenant_insert_policy ON "{table}"'
        )
        bind.exec_driver_sql(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
        bind.exec_driver_sql(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
