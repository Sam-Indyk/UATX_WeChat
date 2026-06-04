"""Tests for the classmates lookup at GET /api/classmates.

Covers:
  - auth required (401 for anon)
  - empty when the signed-in user has no enrollments at all
  - my-side spans past + current + upcoming (any enrollment kind on
    MY side counts toward the classmate pool)
  - the signed-in user is never included in their own classmates list
  - shared courses are grouped per user and limited to the overlap
  - other-side also spans past + current + upcoming, with the OTHER
    user's kind returned per shared course so the UI can color-code
  - dedupe: a classmate enrolled in the same course across multiple
    terms appears once with the highest-priority kind
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


def test_no_enrollments_returns_empty(client) -> None:
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


def test_past_and_upcoming_classmates_appear_with_their_kind(
    client, phil, db, make_user
) -> None:
    """The other side spans past + current + upcoming. Each shared
    course chip carries the OTHER user's kind so the UI can color-code."""
    me = client.current_user
    _enroll(db, user_id=me.id, course_id=phil.id, term="Spring 2026")

    past = make_user(email="past@student.uaustin.org", display_name="PastAlum")
    now = make_user(email="now@student.uaustin.org", display_name="CurrentPeer")
    soon = make_user(email="soon@student.uaustin.org", display_name="UpcomingPeer")
    _enroll(db, user_id=past.id, course_id=phil.id, term="Fall 2024", kind="past")
    _enroll(db, user_id=now.id, course_id=phil.id, term="Spring 2026", kind="current")
    _enroll(db, user_id=soon.id, course_id=phil.id, term="Fall 2026", kind="upcoming")

    rows = client.get("/api/classmates").json()
    by_id = {r["id"]: r for r in rows}
    assert set(by_id) == {past.id, now.id, soon.id}
    assert by_id[past.id]["shared_courses"][0]["kind"] == "past"
    assert by_id[now.id]["shared_courses"][0]["kind"] == "current"
    assert by_id[soon.id]["shared_courses"][0]["kind"] == "upcoming"


def test_my_side_spans_all_kinds(client, phil, math, db, make_user) -> None:
    """Past and upcoming enrollments on MY side also count. If I took
    PHIL last year and someone is taking it now, we're classmates. If
    I'm registered for MATH next semester and someone took it last
    year, also classmates."""
    me = client.current_user
    _enroll(db, user_id=me.id, course_id=phil.id, term="Fall 2024", kind="past")
    _enroll(db, user_id=me.id, course_id=math.id, term="Fall 2026", kind="upcoming")

    a = make_user(display_name="CurrentInPhil")
    _enroll(db, user_id=a.id, course_id=phil.id, term="Spring 2026", kind="current")

    b = make_user(display_name="TookMathLastYear")
    _enroll(db, user_id=b.id, course_id=math.id, term="Fall 2024", kind="past")

    rows = client.get("/api/classmates").json()
    by_id = {r["id"]: r for r in rows}
    assert set(by_id) == {a.id, b.id}
    assert by_id[a.id]["shared_courses"][0]["code"] == "PHIL 101"
    assert by_id[b.id]["shared_courses"][0]["code"] == "MATH 201"


def test_dedupe_retake_collapses_to_highest_priority_kind(
    client, phil, db, make_user
) -> None:
    """A classmate enrolled in the same course across multiple terms
    (retake) appears once. Priority: current > past > upcoming."""
    me = client.current_user
    _enroll(db, user_id=me.id, course_id=phil.id, term="Spring 2026")

    retaker = make_user(display_name="Retaker")
    _enroll(db, user_id=retaker.id, course_id=phil.id, term="Fall 2024", kind="past")
    _enroll(db, user_id=retaker.id, course_id=phil.id, term="Spring 2026", kind="current")

    rows = client.get("/api/classmates").json()
    assert len(rows) == 1
    assert len(rows[0]["shared_courses"]) == 1  # deduped
    assert rows[0]["shared_courses"][0]["kind"] == "current"  # current beats past


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


def test_classmate_dm_conversation_id_null_until_dm_exists(client, phil, db, make_user) -> None:
    me = client.current_user
    _enroll(db, user_id=me.id, course_id=phil.id, term="Spring 2026")
    other = make_user(display_name="Eitan")
    _enroll(db, user_id=other.id, course_id=phil.id, term="Spring 2026")

    rows = client.get("/api/classmates").json()
    assert len(rows) == 1
    assert rows[0]["dm_conversation_id"] is None
    assert rows[0]["unread_count"] == 0


def test_classmate_dm_conversation_id_set_after_dm_created(client, phil, db, make_user) -> None:
    me = client.current_user
    _enroll(db, user_id=me.id, course_id=phil.id, term="Spring 2026")
    other = make_user(display_name="Eitan")
    _enroll(db, user_id=other.id, course_id=phil.id, term="Spring 2026")

    # Create the DM
    dm_id = client.post(f"/api/users/{other.id}/dm").json()["id"]

    rows = client.get("/api/classmates").json()
    assert rows[0]["dm_conversation_id"] == dm_id


def test_classmate_unread_count_reflects_incoming_dms(client, phil, db, make_user) -> None:
    me = client.current_user
    _enroll(db, user_id=me.id, course_id=phil.id, term="Spring 2026")
    other = make_user(display_name="Eitan")
    _enroll(db, user_id=other.id, course_id=phil.id, term="Spring 2026")

    # Create DM, classmate sends two messages
    dm_id = client.post(f"/api/users/{other.id}/dm").json()["id"]
    client.set_user(other)
    client.post(f"/api/conversations/{dm_id}/messages", json={"body": "yo"})
    client.post(f"/api/conversations/{dm_id}/messages", json={"body": "ping"})

    # Back to me
    client.set_user(me)
    rows = client.get("/api/classmates").json()
    assert rows[0]["unread_count"] == 2


def test_classmate_unread_excludes_my_own_outgoing(client, phil, db, make_user) -> None:
    me = client.current_user
    _enroll(db, user_id=me.id, course_id=phil.id, term="Spring 2026")
    other = make_user(display_name="Eitan")
    _enroll(db, user_id=other.id, course_id=phil.id, term="Spring 2026")

    dm_id = client.post(f"/api/users/{other.id}/dm").json()["id"]
    client.post(f"/api/conversations/{dm_id}/messages", json={"body": "from me"})

    rows = client.get("/api/classmates").json()
    assert rows[0]["unread_count"] == 0
