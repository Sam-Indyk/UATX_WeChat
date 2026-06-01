from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.auth import require_user
from app.db import get_db
from app.models import Conversation, Enrollment, Listing, Message, User
from app.schemas.common import (
    EnrollmentIn,
    EnrollmentOut,
    MeUpdate,
    UnreadCountOut,
    UserOut,
)


router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("", response_model=UserOut)
def get_me(user: User = Depends(require_user)) -> User:
    return user


@router.patch("", response_model=UserOut)
def update_me(
    payload: MeUpdate,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> User:
    """Let the signed-in user edit their own profile.

    Right now just display_name. Email is sourced from the JWT and not
    user-editable. Avatar comes from Clerk via the JWT claims (when the
    JWT template includes `picture`).
    """
    if payload.display_name is not None:
        new_name = payload.display_name.strip()
        if not new_name:
            raise HTTPException(status_code=422, detail="display_name cannot be blank")
        user.display_name = new_name

    db.commit()
    db.refresh(user)
    return user


@router.get("/enrollments", response_model=list[EnrollmentOut])
def list_my_enrollments(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[Enrollment]:
    stmt = (
        select(Enrollment)
        .options(joinedload(Enrollment.course))
        .where(Enrollment.user_id == user.id)
        .order_by(Enrollment.is_current.desc(), Enrollment.term.desc())
    )
    return list(db.execute(stmt).scalars().all())


@router.post("/enrollments", response_model=EnrollmentOut, status_code=201)
def add_enrollment(
    payload: EnrollmentIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> Enrollment:
    enr = Enrollment(
        user_id=user.id,
        course_id=payload.course_id,
        term=payload.term,
        is_current=payload.is_current,
    )
    db.add(enr)
    db.commit()
    db.refresh(enr)
    # Eager-load course for the response model
    db.refresh(enr, attribute_names=["course"])
    return enr


@router.get("/unread-count", response_model=UnreadCountOut)
def my_unread_count(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> UnreadCountOut:
    """Count of messages addressed to me that I haven't seen yet.

    A message is "for me" if I'm in the conversation (as buyer or as the
    listing's seller) AND I'm not the sender. Powers the red badge on the
    Inbox link in the top nav.
    """
    stmt = (
        select(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .join(Listing, Conversation.listing_id == Listing.id)
        .where(
            Message.sender_id != user.id,
            Message.read_at.is_(None),
            or_(Conversation.buyer_id == user.id, Listing.seller_id == user.id),
        )
    )
    count = db.execute(stmt).scalar() or 0
    return UnreadCountOut(count=count)
