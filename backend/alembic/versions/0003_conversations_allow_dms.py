"""allow listing-less direct-message conversations

Revision ID: 0003_conversations_allow_dms
Revises: 0002_seed_courses
Create Date: 2026-06-01

Three changes to the conversations table so we can have DMs between
classmates that aren't tied to a listing:

1. `listing_id` becomes nullable (was NOT NULL).
2. New `other_user_id` column: the other party. For existing listing-
   scoped rows this is backfilled from `listings.seller_id`. For new
   DMs, the application stores it explicitly. Having it on the
   conversation row means membership checks don't have to JOIN listings.
3. The old UNIQUE(listing_id, buyer_id) constraint is replaced. For
   listing convos we still want one (listing, buyer) pair; for DMs we
   need (buyer, other_user) uniqueness with listing_id IS NULL. We use
   two partial unique indexes to express both rules clearly.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_conversations_allow_dms"
down_revision: Union[str, None] = "0002_seed_courses"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. listing_id nullable.
    op.alter_column("conversations", "listing_id", existing_type=sa.dialects.postgresql.UUID(as_uuid=True), nullable=True)

    # 2. other_user_id column (nullable initially so we can backfill).
    op.add_column("conversations", sa.Column("other_user_id", sa.String(64), nullable=True))

    # Backfill from listings.seller_id for existing listing-scoped rows.
    op.execute(
        """
        UPDATE conversations c
        SET other_user_id = l.seller_id
        FROM listings l
        WHERE c.listing_id = l.id AND c.other_user_id IS NULL
        """
    )

    # Now make it NOT NULL with the FK.
    op.alter_column("conversations", "other_user_id", existing_type=sa.String(64), nullable=False)
    op.create_foreign_key(
        "fk_conversations_other_user",
        "conversations",
        "users",
        ["other_user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 3. Replace the unique constraint with two partial unique indexes.
    op.drop_constraint("uq_conversation_listing_buyer", "conversations", type_="unique")

    # Listing convos: one (listing, buyer) pair per conversation.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_conversation_listing
        ON conversations (listing_id, buyer_id)
        WHERE listing_id IS NOT NULL
        """
    )

    # DMs: one (buyer, other_user) pair per conversation. The application
    # canonicalizes so that buyer_id < other_user_id for DMs — this index
    # then prevents (A,B) and (B,A) from existing simultaneously.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_conversation_dm
        ON conversations (buyer_id, other_user_id)
        WHERE listing_id IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_conversation_dm")
    op.execute("DROP INDEX IF EXISTS uq_conversation_listing")
    op.create_unique_constraint(
        "uq_conversation_listing_buyer",
        "conversations",
        ["listing_id", "buyer_id"],
    )
    op.drop_constraint("fk_conversations_other_user", "conversations", type_="foreignkey")
    op.drop_column("conversations", "other_user_id")
    op.alter_column("conversations", "listing_id", existing_type=sa.dialects.postgresql.UUID(as_uuid=True), nullable=False)
