"""Tests for the three-state enrollment kind: past / current / upcoming.

The matching algorithm needs to surface listings for the courses I'm
*about to take* (upcoming), not just the ones I'm in now. And listings
from sellers with `upcoming` enrollments should NOT count — those
sellers haven't taken the class yet, so they can't have the book.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models import Course, Enrollment, Listing


@pytest.fixture()
def phil(db: Session) -> Course:
    c = Course(id=uuid.uuid4(), code="PHIL 101", title="Intro to Philosophy")
    db.add(c)
    db.commit()
    return c


def _enroll(db, *, user_id, course_id, term, kind):
    db.add(Enrollment(id=uuid.uuid4(), user_id=user_id, course_id=course_id, term=term, kind=kind))
    db.commit()


def _listing(db, *, seller_id, course_id):
    l = Listing(
        id=uuid.uuid4(),
        seller_id=seller_id,
        course_id=course_id,
        book_title="Republic",
        book_author="Plato",
        condition="good",
        price_cents=1500,
        description="",
    )
    db.add(l)
    db.commit()
    db.refresh(l)
    return l


def test_match_includes_upcoming_courses(client, phil, db, make_user) -> None:
    """A freshman with PHIL 101 marked `upcoming` should still see listings
    from upperclassmen who took it.
    """
    me = client.current_user
    _enroll(db, user_id=me.id, course_id=phil.id, term="Fall 2026", kind="upcoming")

    seller = make_user(email="senior@student.uaustin.org")
    _enroll(db, user_id=seller.id, course_id=phil.id, term="Fall 2024", kind="past")
    _listing(db, seller_id=seller.id, course_id=phil.id)

    rows = client.get("/api/match").json()
    assert len(rows) == 1
    assert "Fall 2024" in rows[0]["rationale"]


def test_match_excludes_past_courses_for_buyer(client, phil, db, make_user) -> None:
    """If I already took PHIL 101 (past), I don't need the book — match
    shouldn't surface it for me.
    """
    me = client.current_user
    _enroll(db, user_id=me.id, course_id=phil.id, term="Fall 2024", kind="past")

    seller = make_user(email="other@student.uaustin.org")
    _enroll(db, user_id=seller.id, course_id=phil.id, term="Fall 2024", kind="past")
    _listing(db, seller_id=seller.id, course_id=phil.id)

    rows = client.get("/api/match").json()
    assert rows == []


def test_match_seller_with_only_upcoming_enrollment_not_credited(client, phil, db, make_user) -> None:
    """A seller who has only `upcoming` enrollment for the course hasn't
    actually taken the class yet — their listing shouldn't claim they
    "took" it. The rationale string falls back to the "no enrollment"
    phrasing.
    """
    me = client.current_user
    _enroll(db, user_id=me.id, course_id=phil.id, term="Spring 2026", kind="current")

    seller = make_user(email="future@student.uaustin.org")
    _enroll(db, user_id=seller.id, course_id=phil.id, term="Fall 2026", kind="upcoming")
    _listing(db, seller_id=seller.id, course_id=phil.id)

    rows = client.get("/api/match").json()
    assert len(rows) == 1
    # No past/current term to credit, so rationale is the fallback.
    assert "took" not in rows[0]["rationale"] or "hasn't" in rows[0]["rationale"]


def test_enrollment_upsert_updates_kind_on_repeat(client, phil) -> None:
    """Posting the same (course, term) twice updates the kind instead of
    creating a duplicate row."""
    a = client.post(
        "/api/me/enrollments",
        json={"course_id": str(phil.id), "term": "Spring 2026", "kind": "current"},
    )
    assert a.status_code == 201
    enr_id = a.json()["id"]

    b = client.post(
        "/api/me/enrollments",
        json={"course_id": str(phil.id), "term": "Spring 2026", "kind": "upcoming"},
    )
    assert b.status_code == 201
    assert b.json()["id"] == enr_id  # same row, not a new one
    assert b.json()["kind"] == "upcoming"


def test_enrollment_kind_validation(client, phil) -> None:
    r = client.post(
        "/api/me/enrollments",
        json={"course_id": str(phil.id), "term": "Spring 2026", "kind": "maybe"},
    )
    assert r.status_code == 422


def test_delete_enrollment(client, phil, db) -> None:
    me = client.current_user
    _enroll(db, user_id=me.id, course_id=phil.id, term="Spring 2026", kind="current")
    enrs = client.get("/api/me/enrollments").json()
    assert len(enrs) == 1
    enr_id = enrs[0]["id"]

    r = client.delete(f"/api/me/enrollments/{enr_id}")
    assert r.status_code == 204
    assert client.get("/api/me/enrollments").json() == []


def test_delete_someone_elses_enrollment_403(client, phil, db, make_user) -> None:
    other = make_user(email="other@student.uaustin.org")
    _enroll(db, user_id=other.id, course_id=phil.id, term="Spring 2026", kind="current")
    their_enr = db.execute(
        Enrollment.__table__.select().where(Enrollment.user_id == other.id)
    ).first()
    r = client.delete(f"/api/me/enrollments/{their_enr.id}")
    assert r.status_code == 403


def test_enrollments_list_ordered_current_then_upcoming_then_past(client, phil, db) -> None:
    """Onboarding wants current first (the courses I'm in now), then
    upcoming (courses I'll need books for), then past.
    """
    math = Course(id=uuid.uuid4(), code="MATH 201", title="Calculus I")
    poli = Course(id=uuid.uuid4(), code="EPH 101", title="Politics")
    db.add_all([math, poli])
    db.commit()

    me = client.current_user
    _enroll(db, user_id=me.id, course_id=phil.id, term="Fall 2024", kind="past")
    _enroll(db, user_id=me.id, course_id=math.id, term="Fall 2026", kind="upcoming")
    _enroll(db, user_id=me.id, course_id=poli.id, term="Spring 2026", kind="current")

    codes = [e["course"]["code"] for e in client.get("/api/me/enrollments").json()]
    assert codes == ["EPH 101", "MATH 201", "PHIL 101"]
