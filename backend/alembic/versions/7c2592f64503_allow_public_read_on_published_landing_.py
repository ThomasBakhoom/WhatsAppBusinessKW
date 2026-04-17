"""allow_public_read_on_published_landing_pages

Landing pages have a public endpoint (`/v1/landing-pages/public/{slug}`)
that serves published pages WITHOUT authentication. Under the `app_user`
role, the default RLS policy requires `app.current_tenant` to be set,
which an unauthenticated request can't do. This makes every published
landing page return 404 — a production-visible bug.

Fix: add a SELECT-only policy on `landing_pages` that allows reads when
`status = 'published'`, regardless of tenant context. PostgreSQL ORs
policies for the same command type, so a SELECT succeeds if EITHER the
tenant matches (authenticated management) OR the page is published
(public read). INSERT/UPDATE/DELETE still require tenant context because
no public-write policy exists.

Revision ID: 7c2592f64503
Revises: 1bde970a88d3
Create Date: 2026-04-16
"""
from typing import Sequence, Union

from alembic import op


revision: str = "7c2592f64503"
down_revision: Union[str, None] = "1bde970a88d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(
        "DROP POLICY IF EXISTS public_read_published ON landing_pages"
    )
    bind.exec_driver_sql(
        """
        CREATE POLICY public_read_published ON landing_pages
        FOR SELECT
        USING (status = 'published')
        """
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        "DROP POLICY IF EXISTS public_read_published ON landing_pages"
    )
