"""replace enrollments.is_current with a three-state kind enum

Revision ID: 0005_enrollment_kind
Revises: 0004_listing_image_url
Create Date: 2026-06-01

Why: a boolean can't tell us that a freshman is ABOUT to take PHIL 101
next semester (they need the book) versus a senior who took it three
years ago (they already have the book and might sell). The marketplace
matching gets richer once we know which of those a row is.

Migration:
1. Add `kind` (TEXT) nullable.
2. Backfill: is_current=true -> 'current', is_current=false -> 'past'.
   We have no upcoming data yet — users will set that via the
   re-skinned Onboarding page.
3. Make kind NOT NULL + CHECK constraint.
4. Drop is_current.

Downgrade reverses: restore is_current boolean (true iff kind='current'),
drop kind.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_enrollment_kind"
down_revision: Union[str, None] = "0004_listing_image_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("enrollments", sa.Column("kind", sa.String(10), nullable=True))
    op.execute(
        """
        UPDATE enrollments
        SET kind = CASE WHEN is_current THEN 'current' ELSE 'past' END
        """
    )
    op.alter_column("enrollments", "kind", existing_type=sa.String(10), nullable=False)
    op.create_check_constraint(
        "ck_enrollment_kind",
        "enrollments",
        "kind IN ('past', 'current', 'upcoming')",
    )
    op.drop_column("enrollments", "is_current")


def downgrade() -> None:
    op.add_column(
        "enrollments",
        sa.Column("is_current", sa.Boolean(), nullable=True),
    )
    op.execute("UPDATE enrollments SET is_current = (kind = 'current')")
    op.alter_column(
        "enrollments",
        "is_current",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.false(),
    )
    op.drop_constraint("ck_enrollment_kind", "enrollments", type_="check")
    op.drop_column("enrollments", "kind")
