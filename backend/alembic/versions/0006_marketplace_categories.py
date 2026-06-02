"""rename book_* fields and add category to listings

Revision ID: 0006_marketplace_categories
Revises: 0005_enrollment_kind
Create Date: 2026-06-01

Generalizes the listings table so non-book items (furniture, electronics,
clothing, etc.) can live alongside textbooks. Three changes:

1. Rename book_title -> title (still NOT NULL).
2. Rename book_author -> author, drop NOT NULL (books still set it; general
   items don't have an author).
3. Rename book_edition -> edition (still NULLABLE).
4. Add category TEXT NOT NULL with CHECK constraint. Backfill 'book' for
   every existing row (every listing today is a book).

Downgrade reverses the rename/category steps.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_marketplace_categories"
down_revision: Union[str, None] = "0005_enrollment_kind"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATEGORIES = (
    "book",
    "furniture",
    "electronics",
    "clothing",
    "kitchen",
    "decor",
    "sports",
    "transportation",
    "other",
)


def upgrade() -> None:
    op.alter_column("listings", "book_title", new_column_name="title")
    op.alter_column(
        "listings",
        "book_author",
        new_column_name="author",
        existing_type=sa.String(200),
        nullable=True,
    )
    op.alter_column("listings", "book_edition", new_column_name="edition")

    op.add_column("listings", sa.Column("category", sa.String(20), nullable=True))
    op.execute("UPDATE listings SET category = 'book'")
    op.alter_column("listings", "category", existing_type=sa.String(20), nullable=False)
    op.create_check_constraint(
        "ck_listing_category",
        "listings",
        "category IN " + repr(CATEGORIES),
    )


def downgrade() -> None:
    op.drop_constraint("ck_listing_category", "listings", type_="check")
    op.drop_column("listings", "category")
    op.alter_column("listings", "edition", new_column_name="book_edition")
    # author was nullable; on downgrade we backfill empty string for any
    # non-book rows so we can re-add NOT NULL.
    op.execute("UPDATE listings SET author = '' WHERE author IS NULL")
    op.alter_column(
        "listings",
        "author",
        new_column_name="book_author",
        existing_type=sa.String(200),
        nullable=False,
    )
    op.alter_column("listings", "title", new_column_name="book_title")
