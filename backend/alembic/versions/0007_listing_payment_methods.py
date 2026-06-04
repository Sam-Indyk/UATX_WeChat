"""add payment_methods array to listings

Revision ID: 0007_listing_payment_methods
Revises: 0006_marketplace_categories
Create Date: 2026-06-04

Adds a `payment_methods text[]` column to `listings` so sellers can
declare which payment methods they're willing to accept (cash, Venmo,
Zelle, PayPal, Stripe). The valid set is enforced at the API layer via
a Pydantic Literal — keeping a Postgres CHECK constraint on array
contents adds complexity for little value and would tie schema changes
to enum changes.

Defaults to an empty array. Existing listings stay valid post-migration
(they just don't have any methods listed yet).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0007_listing_payment_methods"
down_revision: Union[str, None] = "0006_marketplace_categories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "listings",
        sa.Column(
            "payment_methods",
            postgresql.ARRAY(sa.String),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("listings", "payment_methods")
