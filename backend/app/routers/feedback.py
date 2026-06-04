from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import require_user
from app.db import get_db
from app.models import FeedbackSubmission, User
from app.schemas.common import FeedbackCreate, FeedbackOut


router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackOut, status_code=201)
def submit_feedback(
    payload: FeedbackCreate,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> FeedbackSubmission:
    """Capture a user-submitted feature request, bug report, or general
    comment. Stored in feedback_submissions; teammates read via psql /
    Supabase. No moderation UI yet — that's a follow-up.
    """
    submission = FeedbackSubmission(
        user_id=user.id,
        category=payload.category,
        body=payload.body.strip(),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission
