"""add_performance_indexes

Composite indexes targeting the most common query patterns: list endpoints
for contacts, conversations, deals, audit logs, subscriptions, shipments,
and campaign recipients. Every index leads with company_id (tenant filter)
and includes the columns used in WHERE + ORDER BY to enable index-only scans.

Revision ID: ecc08a5666f9
Revises: 7c2592f64503
Create Date: 2026-04-16
"""
from typing import Sequence, Union

from alembic import op


revision: str = "ecc08a5666f9"
down_revision: Union[str, None] = "7c2592f64503"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEXES = [
    # Contacts: list with soft-delete filter + date sort
    ("ix_contact_co_deleted_created", "contacts", "(company_id, deleted_at, created_at DESC)"),
    # Conversations: list with assigned-agent filter + recency sort
    ("ix_conv_co_assigned_last_msg", "conversations", "(company_id, assigned_to_user_id, last_message_at DESC NULLS LAST)"),
    # Deals: kanban board loads by pipeline, sorted by position
    ("ix_deal_co_pipeline_pos", "deals", "(company_id, pipeline_id, deleted_at, position)"),
    # Audit logs: filtered by resource_type + action, date-sorted
    ("ix_audit_co_resource_created", "audit_logs", "(company_id, resource_type, created_at DESC)"),
    # Subscriptions: lookup active sub for a company
    ("ix_sub_co_status_created", "subscriptions", "(company_id, status, created_at DESC)"),
    # Shipments: list with status filter
    ("ix_ship_co_status_created", "shipments", "(company_id, status, created_at DESC)"),
    # Campaign recipients: bulk status updates
    ("ix_camp_recip_status", "campaign_recipients", "(campaign_id, status)"),
]


def upgrade() -> None:
    bind = op.get_bind()
    for name, table, cols in INDEXES:
        bind.exec_driver_sql(
            f"CREATE INDEX IF NOT EXISTS {name} ON {table} {cols}"
        )


def downgrade() -> None:
    bind = op.get_bind()
    for name, _, _ in INDEXES:
        bind.exec_driver_sql(f"DROP INDEX IF EXISTS {name}")
