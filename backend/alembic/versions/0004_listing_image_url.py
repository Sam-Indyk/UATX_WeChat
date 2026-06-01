"""add image_url to listings

Revision ID: 0004_listing_image_url
Revises: 0003_conversations_allow_dms
Create Date: 2026-06-01

Optional photo per listing. Stored in Supabase Storage; this column
holds the public URL (or NULL if no image was uploaded).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_listing_image_url"
down_revision: Union[str, None] = "0003_conversations_allow_dms"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("image_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("listings", "image_url")
