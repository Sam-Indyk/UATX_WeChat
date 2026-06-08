"""UATX Wordle — per-user completion tracking.

The game itself runs entirely on the frontend (word list, guess
matching, color highlighting). The backend's only job is to persist
per-user wins so the Wordle hub page can show "won in N" status per
game across sessions and devices.

We store wins only. Losses don't take a row — a user can retry
indefinitely until they win. On a win, we upsert into the (user_id,
game_index) row with the BEST attempt (fewest guesses), so the
recorded score only improves.

GET  /api/wordle/me               → my completions, one row per game I've won
POST /api/wordle/complete         → record a win
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_user
from app.db import get_db
from app.models import User, WordleCompletion


router = APIRouter(prefix="/api/wordle", tags=["wordle"])


class WordleCompletionCreate(BaseModel):
    # The index into the frontend's WORDLE_WORDS array. Backend doesn't
    # know the word — it just persists the index so the hub page can
    # show per-game status.
    game_index: int = Field(ge=0)
    num_guesses: int = Field(ge=1, le=100)


class WordleCompletionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    game_index: int
    num_guesses: int
    created_at: datetime


@router.get("/me", response_model=list[WordleCompletionOut])
def list_my_completions(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[WordleCompletion]:
    rows = list(
        db.execute(
            select(WordleCompletion)
            .where(WordleCompletion.user_id == user.id)
            .order_by(WordleCompletion.game_index)
        )
        .scalars()
        .all()
    )
    return rows


@router.post("/complete", response_model=WordleCompletionOut, status_code=201)
def record_completion(
    payload: WordleCompletionCreate,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> WordleCompletion:
    """Record a win. Idempotent on (user_id, game_index): if a previous
    attempt already exists, update only if the new attempt is BETTER
    (fewer guesses). Otherwise leave the existing record alone and
    return it.
    """
    existing = db.execute(
        select(WordleCompletion).where(
            WordleCompletion.user_id == user.id,
            WordleCompletion.game_index == payload.game_index,
        )
    ).scalar_one_or_none()

    if existing is not None:
        if payload.num_guesses < existing.num_guesses:
            existing.num_guesses = payload.num_guesses
            db.commit()
            db.refresh(existing)
        return existing

    completion = WordleCompletion(
        user_id=user.id,
        game_index=payload.game_index,
        num_guesses=payload.num_guesses,
    )
    db.add(completion)
    db.commit()
    db.refresh(completion)
    return completion
