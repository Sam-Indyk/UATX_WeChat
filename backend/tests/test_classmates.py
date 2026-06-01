"""Tests for the classmates lookup at GET /api/classmates.

Covers:
  - auth required (401 for anon)
  - empty when the signed-in user has no current enrollments
  - non-current enrollments don't count (only is_kind="current")
  - the signed-in user is never included in their own classmates list
  - shared courses are grouped per user and limited to the overlap
"""
import uuid

import pytest
from sqlalchemy.orm import Session

from app.models import Course, Enrollment


@pytest.fixture()
def phil(db: Session) -> Course:
    c = Course(id=uuid.uuid4(), code="PHIL 101", title="Intro to Philosophy")
    db.add(c)
    db.commit()
    return c


@pytest.fixture()
def math(db: Session) -> Course:
    c = Course(id=uuid.uuid4(), code="MATH 201", title="Calculus I")
    db.add(c)
    db.commit()
    return c


def _enroll(
    db: Session,
    *,
    user_id: str,
    course_id: uuid.UUID,
    term: str,
    kind: str = "current",
) -> None:
    db.add(
        Enrollment(
            id=uuid.uuid4(),
            user_id=user_id,
            course_id=course_id,
            term=term,
            kind=kind,
        )
    )
    db.commit()


def test_classmates_requires_auth(anon_client) -> None:
    r = anon_client.get("/api/classmates")
    assert r.status_code == 401


def test_no_current_enrollments_returns_empty(client) -> None:
    r = client.get("/api/classmates")
    assert r.status_code == 200
    assert r.json() == []


def test_groups_shared_courses_per_classmate(client, phil, math, db, make_user) -> None:
    me = client.current_user
    _enroll(db, user_id=me.id, course_id=phil.id, term="Spring 2026")
    _enroll(db, user_id=me.id, course_id=math.id, term="Spring 2026")

    alice = make_user(email="alice@student.uaustin.org", display_name="Alice")
    bob = make_user(email="bob@student.uaustin.org", display_name="Bob")
    _enroll(db, user_id=alice.id, course_id=phil.id, term="Spring 2026")
    _enroll(db, user_id=alice.id, course_id=math.id, term="Spring 2026")
    _enroll(db, user_id=bob.id, course_id=phil.id, term="Spring 2026")

    rows = client.get("/api/classmates").json()
    by_id = {r["id"]: r for r in rows}
    assert set(by_id) == {alice.id, bob.id}
    assert {c["code"] for c in by_id[alice.id]["shared_courses"]} == {"PHIL 101", "MATH 201"}
    assert {c["code"] for c in by_id[bob.id]["shared_courses"]} == {"PHIL 101"}


def test_ignores_non_current_enrollments(client, phil, db, make_user) -> None:
    me = client.current_user
    _enroll(db, user_id=me.id, course_id=phil.id, term="Spring 2026")

    past_classmate = make_user(email="alum@student.uaustin.org")
    _enroll(db, user_id=past_classmate.id, course_id=phil.id, term="Fall 2024", kind="past")

    r = client.get("/api/classmates")
    assert r.status_code == 200
    assert r.json() == []


def test_excludes_self_even_with_duplicate_enrollments(client, phil, db) -> None:
    me = client.current_user
    _enroll(db, user_id=me.id, course_id=phil.id, term="Spring 2026")

    r = client.get("/api/classmates")
    assert r.status_code == 200
    assert r.json() == []


def test_classmates_sorted_by_overlap_count(client, phil, db, make_user) -> None:
    """Most-shared-courses classmate appears first; alphabetical tiebreaker."""
    math = Course(id=uuid.uuid4(), code="MATH 201", title="Calculus I")
    db.add(math)
    db.commit()

    me = client.current_user
    _enroll(db, user_id=me.id, course_id=phil.id, term="Spring 2026")
    _enroll(db, user_id=me.id, course_id=math.id, term="Spring 2026")

    # Anna shares 1 course; Bob shares 2; Cara shares 1 (tiebreaker with Anna).
    anna = make_user(display_name="Anna")
    bob = make_user(display_name="Bob")
    cara = make_user(display_name="Cara")
    _enroll(db, user_id=anna.id, course_id=phil.id, term="Spring 2026")
    _enroll(db, user_id=bob.id, course_id=phil.id, term="Spring 2026")
    _enroll(db, user_id=bob.id, course_id=math.id, term="Spring 2026")
    _enroll(db, user_id=cara.id, course_id=math.id, term="Spring 2026")

    rows = client.get("/api/classmates").json()
    names = [r["display_name"] for r in rows]
    # Bob (2 overlaps) first, then Anna and Cara (1 each, alphabetical).
    assert names == ["Bob", "Anna", "Cara"]
    assert len(rows[0]["shared_courses"]) == 2
    assert len(rows[1]["shared_courses"]) == 1
    assert len(rows[2]["shared_courses"]) == 1


def test_classmates_response_includes_course_titles(client, phil, db, make_user) -> None:
    """Frontend renders titles, not codes — so the response must carry them."""
    me = client.current_user
    _enroll(db, user_id=me.id, course_id=phil.id, term="Spring 2026")
    other = make_user(display_name="Eitan")
    _enroll(db, user_id=other.id, course_id=phil.id, term="Spring 2026")

    rows = client.get("/api/classmates").json()
    assert rows[0]["shared_courses"][0]["title"] == "Intro to Philosophy"
    assert rows[0]["shared_courses"][0]["code"] == "PHIL 101"
