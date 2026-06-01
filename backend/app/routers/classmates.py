"""Classmates lookup: people who share a current course with the signed-in user.

Mirrors the cross-user enrollment query the matching algorithm uses,
but returns *users* (grouped by id with their shared courses) instead
of listings.
"""
from __future__ import annotations

from collections import OrderedDict

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.auth import require_user
from app.db import get_db
from app.models import Conversation, Course, Enrollment, Message, User
from app.schemas.common import ClassmateOut, CourseOut


router = APIRouter(prefix="/api", tags=["classmates"])


@router.get("/classmates", response_model=list[ClassmateOut])
def list_classmates(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[ClassmateOut]:
    my_course_ids = list(
        db.execute(
            select(Enrollment.course_id).where(
                Enrollment.user_id == user.id,
                Enrollment.kind == "current",
            )
        ).scalars()
    )
    if not my_course_ids:
        return []

    rows = db.execute(
        select(User, Course)
        .join(Enrollment, Enrollment.user_id == User.id)
        .join(Course, Course.id == Enrollment.course_id)
        .where(
            Enrollment.kind == "current",
            Enrollment.course_id.in_(my_course_ids),
            User.id != user.id,
        )
        .order_by(User.display_name, Course.code)
    ).all()

    by_user: OrderedDict[str, dict] = OrderedDict()
    for other, course in rows:
        entry = by_user.get(other.id)
        if entry is None:
            entry = {"user": other, "courses": []}
            by_user[other.id] = entry
        entry["courses"].append(course)

    # Sort by overlap count descending (most classes-in-common at the top),
    # then alphabetically by name as a stable tiebreaker.
    sorted_entries = sorted(
        by_user.values(),
        key=lambda v: (-len(v["courses"]), v["user"].display_name.lower()),
    )

    # Find the DM conversation (if any) for each classmate. One batched
    # query. Conversations canonicalize the pair so (me, them) might be
    # stored as either (buyer=me, other=them) or (buyer=them, other=me) —
    # we check both directions.
    classmate_ids = [v["user"].id for v in sorted_entries]
    dm_by_classmate: dict[str, object] = {}  # classmate_id -> conversation_id
    if classmate_ids:
        dm_rows = db.execute(
            select(
                Conversation.id,
                Conversation.buyer_id,
                Conversation.other_user_id,
            ).where(
                Conversation.listing_id.is_(None),
                or_(
                    and_(
                        Conversation.buyer_id == user.id,
                        Conversation.other_user_id.in_(classmate_ids),
                    ),
                    and_(
                        Conversation.other_user_id == user.id,
                        Conversation.buyer_id.in_(classmate_ids),
                    ),
                ),
            )
        ).all()
        for conv_id, buyer_id, other_user_id in dm_rows:
            classmate = other_user_id if buyer_id == user.id else buyer_id
            dm_by_classmate[classmate] = conv_id

    # Unread per DM conversation (incoming messages from the classmate).
    unread_by_classmate: dict[str, int] = {}
    if dm_by_classmate:
        dm_conv_ids = list(dm_by_classmate.values())
        rows = db.execute(
            select(Message.conversation_id, func.count(Message.id))
            .where(
                Message.conversation_id.in_(dm_conv_ids),
                Message.sender_id != user.id,
                Message.read_at.is_(None),
            )
            .group_by(Message.conversation_id)
        ).all()
        unread_by_conv = {cid: count for cid, count in rows}
        for cid, conv_id in dm_by_classmate.items():
            unread_by_classmate[cid] = unread_by_conv.get(conv_id, 0)

    return [
        ClassmateOut(
            id=v["user"].id,
            display_name=v["user"].display_name,
            avatar_url=v["user"].avatar_url,
            shared_courses=[CourseOut.model_validate(c) for c in v["courses"]],
            dm_conversation_id=dm_by_classmate.get(v["user"].id),
            unread_count=unread_by_classmate.get(v["user"].id, 0),
        )
        for v in sorted_entries
    ]
