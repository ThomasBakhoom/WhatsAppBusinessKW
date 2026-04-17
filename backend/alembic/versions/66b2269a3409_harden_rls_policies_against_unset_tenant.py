"""harden_rls_policies_against_unset_tenant

The original RLS policies (migration f56baac2d30e) use
`current_setting('app.current_tenant')::uuid` — STRICT mode. When an endpoint
forgets to set the GUC, or when an explicit `db.commit()` mid-handler ends
the transaction where `SET LOCAL` was in effect, the GUC reverts to an empty
string (Postgres retains the parameter name, not its value, after SET LOCAL
expires). Casting `''` to uuid raises `invalid input syntax for type uuid: ""`
and the request 500s.

Better: return NULL when the GUC is unset/empty, so the policy's
`company_id = NULL` is UNKNOWN, the row is filtered out, and the caller sees
an empty result. This is fail-closed silent rather than fail-closed loud,
and is far more forgiving of code paths that re-commit mid-handler.

The helper `enable_rls` is also updated so future `SELECT enable_rls('t')`
calls use the same hardened form.

Revision ID: 66b2269a3409
Revises: 1cefbd1e74ea
Create Date: 2026-04-15
"""
from typing import Sequence, Union

from alembic import op


revision: str = "66b2269a3409"
down_revision: Union[str, None] = "1cefbd1e74ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Same table list as f56baac2d30e (minus users, which no longer has RLS).
TENANT_TABLES: tuple[str, ...] = (
    "ai_conversation_contexts", "api_keys", "audit_logs", "automation_logs",
    "automations", "campaigns", "channels", "chatbot_flows", "contacts",
    "conversations", "custom_fields", "deals", "glossary_terms", "invoices",
    "landing_pages", "message_templates", "messages", "payments", "pipelines",
    "product_categories", "products", "routing_decisions", "shipments",
    "shipping_providers", "subscriptions", "survey_responses", "surveys",
    "tags", "web_chat_widgets",
)


# Hardened helper. `current_setting(name, true)` returns NULL when the
# parameter has never been set; NULLIF catches the empty-string case that
# arises after SET LOCAL expires at COMMIT.
HARDENED_ENABLE_RLS = """
CREATE OR REPLACE FUNCTION enable_rls(table_name TEXT) RETURNS void AS $$
BEGIN
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS tenant_isolation_policy ON %I', table_name);
    EXECUTE format('DROP POLICY IF EXISTS tenant_insert_policy ON %I', table_name);
    EXECUTE format(
        'CREATE POLICY tenant_isolation_policy ON %I
         FOR ALL
         USING (
             company_id = NULLIF(current_setting(''app.current_tenant'', true), '''')::uuid
         )',
        table_name
    );
    EXECUTE format(
        'CREATE POLICY tenant_insert_policy ON %I
         FOR INSERT
         WITH CHECK (
             company_id = NULLIF(current_setting(''app.current_tenant'', true), '''')::uuid
         )',
        table_name
    );
END;
$$ LANGUAGE plpgsql;
"""

# Legacy (strict) helper, restored on downgrade.
LEGACY_ENABLE_RLS = """
CREATE OR REPLACE FUNCTION enable_rls(table_name TEXT) RETURNS void AS $$
BEGIN
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS tenant_isolation_policy ON %I', table_name);
    EXECUTE format('DROP POLICY IF EXISTS tenant_insert_policy ON %I', table_name);
    EXECUTE format(
        'CREATE POLICY tenant_isolation_policy ON %I
         FOR ALL
         USING (company_id = current_setting(''app.current_tenant'')::uuid)',
        table_name
    );
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
    bind.exec_driver_sql(HARDENED_ENABLE_RLS)
    for t in TENANT_TABLES:
        bind.exec_driver_sql(f"SELECT enable_rls('{t}')")


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(LEGACY_ENABLE_RLS)
    for t in TENANT_TABLES:
        bind.exec_driver_sql(f"SELECT enable_rls('{t}')")
