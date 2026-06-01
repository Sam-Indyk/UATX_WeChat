"""Classmates lookup: people who share a current course with the signed-in user.

Mirrors the cross-user enrollment query the matching algorithm uses,
but returns *users* (grouped by id with their shared courses) instead
of listings.
"""
from __future__ import annotations

from collections import OrderedDict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_user
from app.db import get_db
from app.models import Course, Enrollment, User
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
                Enrollment.is_current.is_(True),
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
            Enrollment.is_current.is_(True),
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

    return [
        ClassmateOut(
            id=v["user"].id,
            display_name=v["user"].display_name,
            avatar_url=v["user"].avatar_url,
            shared_courses=[CourseOut.model_validate(c) for c in v["courses"]],
        )
        for v in by_user.values()
    ]
