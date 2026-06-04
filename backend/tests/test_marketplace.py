"""Tests for the general marketplace ("Everything Else" tab) — non-book
listings with categories.

The biggest invariants:
  - Books require an author; general items don't.
  - Matching only surfaces books, never furniture/electronics/etc.
  - The Everything Else browse (?category=non-book) excludes books AND
    excludes general items without a photo (image_url IS NULL).
"""
import uuid

import pytest
from sqlalchemy.orm import Session

from app.models import Course, Listing


@pytest.fixture()
def course(db: Session) -> Course:
    c = Course(id=uuid.uuid4(), code="PHIL 101", title="Intro to Philosophy")
    db.add(c)
    db.commit()
    return c


def _book_payload(course_id, **overrides) -> dict:
    base = {
        "category": "book",
        "course_id": str(course_id),
        "title": "Republic",
        "author": "Plato",
        "edition": None,
        "condition": "good",
        "price_cents": 1500,
        "description": "",
    }
    base.update(overrides)
    return base


def _item_payload(**overrides) -> dict:
    base = {
        "category": "furniture",
        "title": "Standing desk",
        "condition": "like_new",
        "price_cents": 12000,
        "description": "Comfortable, mostly assembled.",
    }
    base.update(overrides)
    return base


def test_create_book_without_author_allowed(client, course) -> None:
    """Author is optional on books — some are unattributed or compiled.
    The Sell-a-book form lets the seller leave it blank."""
    r = client.post("/api/listings", json=_book_payload(course.id, author=None))
    assert r.status_code == 201
    assert r.json()["author"] is None


def test_create_general_item_works_without_author(client) -> None:
    r = client.post("/api/listings", json=_item_payload())
    assert r.status_code == 201
    body = r.json()
    assert body["category"] == "furniture"
    assert body["author"] is None
    assert body["title"] == "Standing desk"


def test_create_general_item_ignores_course(client, course) -> None:
    """Even if the client sends a course_id with a non-book payload, the
    backend should drop it (general items aren't course-tagged).
    """
    r = client.post(
        "/api/listings",
        json=_item_payload(course_id=str(course.id)),
    )
    assert r.status_code == 201
    assert r.json()["course"] is None


def test_create_rejects_bad_category(client) -> None:
    r = client.post("/api/listings", json=_item_payload(category="weapons"))
    assert r.status_code == 422


def test_browse_non_book_filter_excludes_books(client, course) -> None:
    client.post("/api/listings", json=_book_payload(course.id))
    item_id = client.post("/api/listings", json=_item_payload()).json()["id"]
    # The item has no image yet → won't show on Everything Else. Patch
    # one in directly (skipping the upload endpoint) so we can assert
    # the browse semantics.
    client.patch(f"/api/listings/{item_id}", json={})  # ensure the row exists
    # ↓ direct DB stamp for image_url
    from sqlalchemy import update as sa_update

    from app.models import Listing as ListingModel

    # Reaching into the test session for a quick image_url backfill.
    # (Doing this here keeps the test focused; production has the
    # POST /api/listings/{id}/image endpoint for this.)

    from tests.conftest import _engine  # type: ignore[attr-defined]

    with _engine.begin() as conn:
        conn.execute(
            sa_update(ListingModel)
            .where(ListingModel.id == uuid.UUID(item_id))
            .values(image_url="https://fake/image.png")
        )

    rows = client.get("/api/listings?category=non-book").json()
    titles = [r["title"] for r in rows]
    assert titles == ["Standing desk"]


def test_browse_non_book_excludes_items_without_image(client) -> None:
    client.post("/api/listings", json=_item_payload(title="No-photo bike"))
    rows = client.get("/api/listings?category=non-book").json()
    titles = [r["title"] for r in rows]
    # The just-posted item has no image; should be hidden from the
    # Everything Else browse.
    assert "No-photo bike" not in titles


def test_browse_books_only_with_category_book(client, course) -> None:
    client.post("/api/listings", json=_book_payload(course.id, title="Republic"))
    client.post("/api/listings", json=_item_payload(title="Chair"))

    rows = client.get("/api/listings?category=book").json()
    titles = {r["title"] for r in rows}
    assert "Republic" in titles
    assert "Chair" not in titles


def test_matching_excludes_non_book_listings(client, course, db, make_user) -> None:
    """A user enrolled in PHIL 101 should NEVER see a chair listing in
    /api/match, even if that listing was somehow created with course_id
    set (we currently strip it but defending in the matching layer is
    cheap insurance).
    """
    from app.models import Enrollment

    me = client.current_user
    db.add(
        Enrollment(
            id=uuid.uuid4(),
            user_id=me.id,
            course_id=course.id,
            term="Spring 2026",
            kind="current",
        )
    )
    db.commit()

    seller = make_user(email="seller@student.uaustin.org")
    # Hand-craft a non-book listing WITH course_id set (in case a future
    # PR ever permits it). Matching should still ignore it.
    db.add(
        Listing(
            id=uuid.uuid4(),
            seller_id=seller.id,
            course_id=course.id,
            category="furniture",
            title="Bookshelf",
            condition="good",
            price_cents=4000,
            description="",
        )
    )
    db.commit()

    rows = client.get("/api/match").json()
    assert rows == []


def test_update_general_item_fields(client) -> None:
    item_id = client.post("/api/listings", json=_item_payload()).json()["id"]
    r = client.patch(
        f"/api/listings/{item_id}",
        json={"title": "  Renamed desk  ", "price_cents": 9000, "category": "electronics"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Renamed desk"
    assert body["price_cents"] == 9000
    assert body["category"] == "electronics"
