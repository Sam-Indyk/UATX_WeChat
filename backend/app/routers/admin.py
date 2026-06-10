"""Admin-only endpoints. Gated by `require_admin` (in app/auth.py),
which checks the caller's email against ADMIN_EMAILS in settings.

So far we just expose the feedback inbox — could grow to listing
moderation, user actions (warn / suspend), etc. Keep additions here
behind require_admin so non-admins never get past the door.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.db import get_db
from app.models import FeedbackSubmission, User
from app.schemas.common import FeedbackSubmissionAdminOut


router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/feedback", response_model=list[FeedbackSubmissionAdminOut])
def list_all_feedback(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[FeedbackSubmissionAdminOut]:
    """All feedback submissions across all users, newest first.

    LEFT JOIN on users so deleted authors (ON DELETE SET NULL on the FK)
    still show as a row, just with null user_email / user_display_name.
    """
    rows = db.execute(
        select(
            FeedbackSubmission.id,
            FeedbackSubmission.category,
            FeedbackSubmission.body,
            FeedbackSubmission.created_at,
            FeedbackSubmission.user_id,
            User.email,
            User.display_name,
        )
        .join(User, User.id == FeedbackSubmission.user_id, isouter=True)
        .order_by(desc(FeedbackSubmission.created_at))
    ).all()

    return [
        FeedbackSubmissionAdminOut(
            id=r.id,
            category=r.category,
            body=r.body,
            created_at=r.created_at,
            user_id=r.user_id,
            user_email=r.email,
            user_display_name=r.display_name,
        )
        for r in rows
    ]
