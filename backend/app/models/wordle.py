import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class WordleCompletion(Base):
    __tablename__ = "wordle_completions"
    __table_args__ = (
        UniqueConstraint("user_id", "game_index", name="uq_wordle_user_game"),
        CheckConstraint("num_guesses >= 1", name="wordle_num_guesses_positive"),
        CheckConstraint("game_index >= 0", name="wordle_game_index_nonneg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    game_index: Mapped[int] = mapped_column(Integer, nullable=False)
    num_guesses: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
