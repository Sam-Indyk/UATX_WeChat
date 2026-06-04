"""add stripe_account_id + stripe_onboarded to users

Revision ID: 0008_user_stripe_fields
Revises: 0007_listing_payment_methods
Create Date: 2026-06-04

Tracks each seller's Stripe Connect account so we can route checkout
payments to them. `stripe_account_id` is set the first time the user
clicks "Set up Stripe payments" in /settings — we create an Express
Connect account on their behalf and stash the ID here.

`stripe_onboarded` flips to true after Stripe's `account.updated`
webhook reports `details_submitted` + `charges_enabled`. The
"Pay with Stripe" button on listings only shows when both this flag
AND `payment_methods` containing 'stripe' are true on the seller.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008_user_stripe_fields"
down_revision: Union[str, None] = "0007_listing_payment_methods"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("stripe_account_id", sa.String(64), nullable=True, unique=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "stripe_onboarded",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "stripe_onboarded")
    op.drop_column("users", "stripe_account_id")
