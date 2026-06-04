"""create feedback_submissions table

Revision ID: 0009_feedback_submissions
Revises: 0008_user_stripe_fields
Create Date: 2026-06-04

Lets signed-in users submit free-form feedback (feature requests, bugs,
or any other comment) from a /feedback page. The submissions live in the
DB; we don't (yet) surface them anywhere in the UI for moderators — that's
a follow-up. For now a teammate just reads them via psql / Supabase.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "0009_feedback_submissions"
down_revision: Union[str, None] = "0008_user_stripe_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feedback_submissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        # ON DELETE SET NULL: keep the feedback even if the user is later
        # deleted (it's still useful product input).
        sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "category IN ('feature', 'bug', 'other')",
            name="feedback_submissions_category_check",
        ),
    )
    op.create_index(
        "ix_feedback_submissions_created_at",
        "feedback_submissions",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_feedback_submissions_created_at", table_name="feedback_submissions")
    op.drop_table("feedback_submissions")
