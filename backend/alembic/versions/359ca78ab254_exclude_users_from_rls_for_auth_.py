"""exclude_users_from_rls_for_auth_bootstrap

The `users` table cannot be RLS-enforced via the standard tenant policy
because authentication looks up a user by email BEFORE a tenant context
exists (we don't know the company until we find the user). Forcing the
policy would require the login query to return 0 rows, which breaks login.

Standard multi-tenant SaaS practice (and what e.g. Supabase, Linear, etc.
do): keep RLS OFF the user table and rely on app-level filters
(`WHERE company_id = current_user.company_id`) for every users query.

All endpoints reading users go through `TenantDbSession` (which sets
`app.current_tenant`) and either (a) use SQLAlchemy relationships
(`user.company`) which are FK-bounded, or (b) explicitly filter by
`company_id`. The login flow is the only legitimate cross-tenant
read path, scoped to a single email lookup that returns at most one
row per (company_id, email) due to the unique constraint.

If you add new code paths that touch `users`, you MUST filter by
`company_id` explicitly — this is no longer enforced at the DB layer.

Revision ID: 359ca78ab254
Revises: 85ab1623c66c
Create Date: 2026-04-15
"""
from typing import Sequence, Union

from alembic import op


revision: str = "359ca78ab254"
down_revision: Union[str, None] = "85ab1623c66c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        'DROP POLICY IF EXISTS tenant_isolation_policy ON "users"'
    )
    bind.exec_driver_sql(
        'DROP POLICY IF EXISTS tenant_insert_policy ON "users"'
    )
    bind.exec_driver_sql('ALTER TABLE "users" NO FORCE ROW LEVEL SECURITY')
    bind.exec_driver_sql('ALTER TABLE "users" DISABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("SELECT enable_rls('users')")
