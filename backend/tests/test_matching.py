"""Tests for the bronze nontrivial piece: course-history-based matching.

Covers:
  - empty-enrollment case → empty result
  - own listings excluded
  - non-active listings excluded
  - listings outside enrolled courses excluded
  - recency dominates freshness in the ranking
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


def _enroll(db: Session, *, user_id: str, course_id: uuid.UUID, term: str, current: bool = False) -> None:
    db.add(
        Enrollment(
            id=uuid.uuid4(),
            user_id=user_id,
            course_id=course_id,
            term=term,
            is_current=current,
        )
    )
    db.commit()


def _listing(
    db: Session,
    *,
    seller_id: str,
    course_id: uuid.UUID,
    price_cents: int = 1500,
    status: str = "active",
    created_at: datetime | None = None,
) -> Listing:
    l = Listing(
        id=uuid.uuid4(),
        seller_id=seller_id,
        course_id=course_id,
        book_title="Republic",
        book_author="Plato",
        condition="good",
        price_cents=price_cents,
        description="",
        status=status,
    )
    db.add(l)
    db.commit()
    if created_at is not None:
        db.execute(
            Listing.__table__.update()
            .where(Listing.id == l.id)
            .values(created_at=created_at)
        )
        db.commit()
    db.refresh(l)
    return l


def test_no_enrollments_returns_empty(client) -> None:
    r = client.get("/api/match")
    assert r.status_code == 200
    assert r.json() == []


def test_excludes_own_listings(client, phil, db) -> None:
    _enroll(db, user_id=client.current_user.id, course_id=phil.id, term="Spring 2026", current=True)
    _listing(db, seller_id=client.current_user.id, course_id=phil.id)

    r = client.get("/api/match")
    assert r.status_code == 200
    assert r.json() == []


def test_excludes_non_active_and_other_courses(client, phil, db, make_user) -> None:
    other_course = Course(id=uuid.uuid4(), code="MATH 201", title="Calculus I")
    db.add(other_course)
    db.commit()

    _enroll(db, user_id=client.current_user.id, course_id=phil.id, term="Spring 2026", current=True)
    seller = make_user(email="seller@student.uaustin.org")

    sold = _listing(db, seller_id=seller.id, course_id=phil.id, status="sold")
    other = _listing(db, seller_id=seller.id, course_id=other_course.id)
    good = _listing(db, seller_id=seller.id, course_id=phil.id)

    r = client.get("/api/match")
    assert r.status_code == 200
    ids = [row["id"] for row in r.json()]
    assert ids == [str(good.id)]
    assert str(sold.id) not in ids
    assert str(other.id) not in ids


def test_recent_seller_outranks_old_seller(client, phil, db, make_user) -> None:
    _enroll(db, user_id=client.current_user.id, course_id=phil.id, term="Spring 2026", current=True)

    recent_seller = make_user(email="recent@student.uaustin.org", display_name="Recent")
    old_seller = make_user(email="old@student.uaustin.org", display_name="Old")
    _enroll(db, user_id=recent_seller.id, course_id=phil.id, term="Fall 2024")
    _enroll(db, user_id=old_seller.id, course_id=phil.id, term="Fall 2020")

    # Older listing from recent seller; newer listing from old seller.
    # Without recency, freshness would put old_seller first; with recency,
    # recent_seller wins.
    old_listing = _listing(
        db,
        seller_id=recent_seller.id,
        course_id=phil.id,
        created_at=datetime.now(timezone.utc) - timedelta(days=10),
    )
    _listing(
        db,
        seller_id=old_seller.id,
        course_id=phil.id,
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
    )

    rows = client.get("/api/match").json()
    assert rows[0]["id"] == str(old_listing.id)
    assert "Fall 2024" in rows[0]["rationale"]
