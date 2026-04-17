"""add_resolve_instagram_channel_function

Adds a SECURITY DEFINER function `resolve_instagram_channel(page_id text)` that
returns the owning company/channel for a given Instagram page id.

WHY THIS EXISTS:
Instagram webhooks arrive WITHOUT tenant context — the only identifying
signal in the payload is the page id (`entry[].id`). Our `channels` table
is RLS-protected under `app_user`, so a cross-tenant lookup would return
zero rows. Prior code worked around this by picking "the first active
Instagram channel" across the whole DB, which is a cross-tenant data leak
the moment two customers connect Instagram.

A SECURITY DEFINER function runs with the privileges of the function
OWNER (the schema owner `kwgrowth`, which bypasses RLS) regardless of
who invokes it. We limit the blast radius by:
  - returning ONLY the minimal fields needed to route the event
    (company_id, channel_id, access_token)
  - filtering to Instagram channels only
  - requiring is_active = true

The function is granted to `app_user` so the runtime role can call it.

Revision ID: 1cefbd1e74ea
Revises: 359ca78ab254
Create Date: 2026-04-15
"""
from typing import Sequence, Union

from alembic import op


revision: str = "1cefbd1e74ea"
down_revision: Union[str, None] = "359ca78ab254"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CREATE_FN = """
CREATE OR REPLACE FUNCTION public.resolve_instagram_channel(p_page_id text)
RETURNS TABLE (
    company_id    uuid,
    channel_id    uuid,
    access_token  text
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT
        c.company_id,
        c.id,
        COALESCE(c.credentials ->> 'access_token', '') AS access_token
    FROM public.channels c
    WHERE c.channel_type = 'instagram'
      AND c.is_active    = true
      AND c.credentials ->> 'page_id' = p_page_id
    LIMIT 1;
$$
"""

REVOKE_FROM_PUBLIC = (
    "REVOKE ALL ON FUNCTION public.resolve_instagram_channel(text) FROM PUBLIC"
)
GRANT_TO_APP_USER = (
    "GRANT EXECUTE ON FUNCTION public.resolve_instagram_channel(text) TO app_user"
)
CREATE_INDEX = (
    "CREATE INDEX IF NOT EXISTS ix_channels_instagram_page_id "
    "ON public.channels ((credentials ->> 'page_id')) "
    "WHERE channel_type = 'instagram' AND is_active = true"
)
DROP_INDEX = "DROP INDEX IF EXISTS public.ix_channels_instagram_page_id"
DROP_FN = "DROP FUNCTION IF EXISTS public.resolve_instagram_channel(text)"


def upgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(CREATE_FN)
    bind.exec_driver_sql(REVOKE_FROM_PUBLIC)
    bind.exec_driver_sql(GRANT_TO_APP_USER)
    bind.exec_driver_sql(CREATE_INDEX)


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql(DROP_INDEX)
    bind.exec_driver_sql(DROP_FN)
