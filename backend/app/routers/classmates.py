"""Classmates lookup: people who share at least one of the signed-in
user's courses, across all enrollment kinds (past / current / upcoming)
on BOTH sides.

The query is symmetric — anyone the viewer has ever overlapped with on
any course (whether the viewer took it past, takes it now, or will take
it upcoming) counts as a classmate. Each shared course is returned
annotated with the OTHER user's kind so the frontend can color-code
(see SharedCourseOut).
"""
from __future__ import annotations

from collections import OrderedDict

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.auth import require_user
from app.db import get_db
from app.models import Conversation, Course, Enrollment, Message, User
from app.schemas.common import ClassmateOut, SharedCourseOut


# Priority order for deduping: a classmate enrolled in the SAME course
# both currently and in a past term (legitimate — retake / re-audit)
# should show up once with the most-salient kind. Current beats past
# beats upcoming for the same-class-as-me framing.
_KIND_PRIORITY = {"current": 0, "past": 1, "upcoming": 2}


router = APIRouter(prefix="/api", tags=["classmates"])


@router.get("/classmates", response_model=list[ClassmateOut])
def list_classmates(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[ClassmateOut]:
    # All of the viewer's enrollments count — past / current / upcoming.
    # Distinct because the viewer might have the same course across
    # multiple terms (retake); we just need the set of course IDs.
    my_course_ids = list(
        db.execute(
            select(Enrollment.course_id)
            .where(Enrollment.user_id == user.id)
            .distinct()
        ).scalars()
    )
    if not my_course_ids:
        return []

    # No kind filter on the OTHER user either — anyone enrolled in one
    # of the viewer's courses (in any kind, in any term) is a classmate.
    rows = db.execute(
        select(User, Course, Enrollment.kind)
        .join(Enrollment, Enrollment.user_id == User.id)
        .join(Course, Course.id == Enrollment.course_id)
        .where(
            Enrollment.course_id.in_(my_course_ids),
            User.id != user.id,
        )
        .order_by(User.display_name, Course.code)
    ).all()

    # Dedupe per (classmate, course) pair. A user may have enrolled in
    # the same course across multiple terms (e.g. retake) so the join
    # can produce multiple rows for the same Course; we collapse them
    # by picking the highest-priority kind per course (see _KIND_PRIORITY).
    by_user: OrderedDict[str, dict] = OrderedDict()
    for other, course, kind in rows:
        entry = by_user.get(other.id)
        if entry is None:
            entry = {"user": other, "courses": {}}
            by_user[other.id] = entry
        existing = entry["courses"].get(course.id)
        if existing is None or _KIND_PRIORITY[kind] < _KIND_PRIORITY[existing[1]]:
            entry["courses"][course.id] = (course, kind)

    # Sort by overlap count descending (most classes-in-common at the top),
    # then alphabetically by name as a stable tiebreaker. The overlap
    # count is the number of distinct shared courses (post-dedupe).
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
            shared_courses=[
                SharedCourseOut(id=c.id, code=c.code, title=c.title, kind=k)
                for c, k in v["courses"].values()
            ],
            dm_conversation_id=dm_by_classmate.get(v["user"].id),
            unread_count=unread_by_classmate.get(v["user"].id, 0),
        )
        for v in sorted_entries
    ]
