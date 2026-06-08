"""create wordle_completions table

Revision ID: 0010_wordle_completions
Revises: 0009_feedback_submissions
Create Date: 2026-06-07

Tracks each user's UATX Wordle wins per game. UNIQUE on (user_id,
game_index) so retries don't pile up duplicate rows; the endpoint
upserts with the BEST attempt (fewest guesses) so a user's recorded
score only improves.

Only wins are stored — losses don't take up a row. Drives the per-game
status on the Wordle hub page (won-in-N vs. not-played-yet).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "0010_wordle_completions"
down_revision: Union[str, None] = "0009_feedback_submissions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wordle_completions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.String(64),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("game_index", sa.Integer, nullable=False),
        sa.Column("num_guesses", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "game_index", name="uq_wordle_user_game"),
        sa.CheckConstraint("num_guesses >= 1", name="wordle_num_guesses_positive"),
        sa.CheckConstraint("game_index >= 0", name="wordle_game_index_nonneg"),
    )


def downgrade() -> None:
    op.drop_table("wordle_completions")
