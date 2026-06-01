import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, case, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.auth import require_user
from app.db import get_db
from app.models import Conversation, Enrollment, Listing, Message, User
from app.schemas.common import (
    EnrollmentIn,
    EnrollmentOut,
    ListingOut,
    MeUpdate,
    UnreadCountOut,
    UnreadCountsOut,
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


@router.get("/unread-counts", response_model=UnreadCountsOut)
def my_unread_counts(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> UnreadCountsOut:
    """Per-context unread breakdown for the three-badge nav.

    For listing convos, `other_user_id` is the seller (we denormalize at
    creation), so:
      - I'm the seller iff (listing_id IS NOT NULL AND other_user_id = me)
      - I'm the buyer  iff (listing_id IS NOT NULL AND buyer_id = me)
    For DMs, listing_id IS NULL.

    One query with three SUM(CASE) clauses — avoids three round-trips.
    """
    stmt = (
        select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Conversation.listing_id.is_not(None),
                                Conversation.other_user_id == user.id,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("listings"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Conversation.listing_id.is_not(None),
                                Conversation.buyer_id == user.id,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("inquiries"),
            func.coalesce(
                func.sum(
                    case((Conversation.listing_id.is_(None), 1), else_=0)
                ),
                0,
            ).label("dms"),
        )
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Message.sender_id != user.id,
            Message.read_at.is_(None),
            or_(Conversation.buyer_id == user.id, Conversation.other_user_id == user.id),
        )
    )
    row = db.execute(stmt).one()
    listings = int(row.listings or 0)
    inquiries = int(row.inquiries or 0)
    dms = int(row.dms or 0)
    return UnreadCountsOut(
        listings=listings,
        inquiries=inquiries,
        dms=dms,
        total=listings + inquiries + dms,
    )


@router.get("/listings", response_model=list[ListingOut])
def my_listings(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[Listing]:
    """Listings the signed-in user posted, newest first, each with
    `unread_count` = how many incoming messages across this listing's
    conversations the seller hasn't read yet. Powers `/my-listings`.
    """
    listings = list(
        db.execute(
            select(Listing)
            .options(joinedload(Listing.seller), joinedload(Listing.course))
            .where(Listing.seller_id == user.id)
            .order_by(desc(Listing.created_at))
        )
        .scalars()
        .unique()
        .all()
    )

    if listings:
        listing_ids = [l.id for l in listings]
        rows = db.execute(
            select(Conversation.listing_id, func.count(Message.id))
            .join(Message, Message.conversation_id == Conversation.id)
            .where(
                Conversation.listing_id.in_(listing_ids),
                Message.sender_id != user.id,
                Message.read_at.is_(None),
            )
            .group_by(Conversation.listing_id)
        ).all()
        unread_by_listing = {lid: count for lid, count in rows}
        for l in listings:
            l.unread_count = unread_by_listing.get(l.id, 0)

    return listings
