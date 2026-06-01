import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.auth import require_user
from app.db import get_db
from app.models import Conversation, Enrollment, Message, User
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
    # Order: current first (most relevant for "books I need now"), then
    # upcoming, then past. Within a group, most recent term first.
    kind_order = case(
        (Enrollment.kind == "current", 0),
        (Enrollment.kind == "upcoming", 1),
        (Enrollment.kind == "past", 2),
        else_=3,
    )
    stmt = (
        select(Enrollment)
        .options(joinedload(Enrollment.course))
        .where(Enrollment.user_id == user.id)
        .order_by(kind_order, Enrollment.term.desc())
    )
    return list(db.execute(stmt).scalars().all())


@router.post("/enrollments", response_model=EnrollmentOut, status_code=201)
def upsert_enrollment(
    payload: EnrollmentIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> Enrollment:
    """Create or update an enrollment.

    Upserts on (user_id, course_id, term). If the row exists we update
    the `kind`; otherwise we insert. This is what the Onboarding page
    calls when the user changes a course from "past" to "current" etc.
    """
    existing = db.execute(
        select(Enrollment).where(
            Enrollment.user_id == user.id,
            Enrollment.course_id == payload.course_id,
            Enrollment.term == payload.term,
        )
    ).scalar_one_or_none()

    if existing is not None:
        existing.kind = payload.kind
        db.commit()
        db.refresh(existing, attribute_names=["course"])
        return existing

    enr = Enrollment(
        user_id=user.id,
        course_id=payload.course_id,
        term=payload.term,
        kind=payload.kind,
    )
    db.add(enr)
    db.commit()
    db.refresh(enr)
    db.refresh(enr, attribute_names=["course"])
    return enr


@router.delete("/enrollments/{enrollment_id}", status_code=204)
def delete_enrollment(
    enrollment_id: uuid.UUID,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove an enrollment. Used when the user picks 'Not enrolled' for
    a course in Onboarding that they had previously marked.
    """
    enr = db.get(Enrollment, enrollment_id)
    if enr is None:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    if enr.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not your enrollment")
    db.delete(enr)
    db.commit()


@router.get("/unread-count", response_model=UnreadCountOut)
def my_unread_count(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> UnreadCountOut:
    """Count of messages addressed to me that I haven't seen yet.

    Includes both listing-scoped conversations and direct messages. A
    message counts if I'm in the conversation (`buyer_id` or
    `other_user_id`) and I'm not the sender. Powers the red badge on
    the Inbox link in the top nav.
    """
    stmt = (
        select(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Message.sender_id != user.id,
            Message.read_at.is_(None),
            or_(Conversation.buyer_id == user.id, Conversation.other_user_id == user.id),
        )
    )
    count = db.execute(stmt).scalar() or 0
    return UnreadCountOut(count=count)
