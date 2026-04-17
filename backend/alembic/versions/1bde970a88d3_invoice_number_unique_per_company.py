"""invoice_number_unique_per_company

Fixes a multi-tenant bug: the old unique constraint on invoice_number was
global, so two companies creating their first invoice in the same month
would collide on INV-202604-0001. The new constraint scopes by company_id.

Revision ID: 1bde970a88d3
Revises: 66b2269a3409
Create Date: 2026-04-16
"""
from typing import Sequence, Union

from alembic import op


revision: str = "1bde970a88d3"
down_revision: Union[str, None] = "66b2269a3409"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("invoices_invoice_number_key", "invoices", type_="unique")
    op.create_unique_constraint(
        "uq_invoice_company_number", "invoices", ["company_id", "invoice_number"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_invoice_company_number", "invoices", type_="unique")
    op.create_unique_constraint(
        "invoices_invoice_number_key", "invoices", ["invoice_number"]
    )
