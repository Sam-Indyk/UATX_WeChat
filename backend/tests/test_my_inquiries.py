"""Tests for GET /api/me/inquiries — the buyer's home for shopping
conversations. Symmetric with /api/me/listings (seller's side).
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


def test_inquiries_empty_for_new_user(client) -> None:
    r = client.get("/api/me/inquiries")
    assert r.status_code == 200
    assert r.json() == []


def test_inquiries_returns_my_buying_conversations(client, make_user, course, db) -> None:
    me = client.current_user
    seller = make_user(email="seller@student.uaustin.org", display_name="Seller")
    listing = Listing(
        id=uuid.uuid4(),
        seller_id=seller.id,
        course_id=course.id,
        book_title="Republic",
        book_author="Plato",
        condition="good",
        price_cents=1500,
        description="",
    )
    db.add(listing)
    db.commit()

    convo_id = client.post(f"/api/listings/{listing.id}/contact").json()["id"]
    rows = client.get("/api/me/inquiries").json()
    assert len(rows) == 1
    assert rows[0]["id"] == convo_id
    assert rows[0]["listing"]["book_title"] == "Republic"


def test_inquiries_excludes_dms(client, make_user) -> None:
    other = make_user(email="other@student.uaustin.org")
    client.post(f"/api/users/{other.id}/dm")

    rows = client.get("/api/me/inquiries").json()
    assert rows == []


def test_inquiries_excludes_seller_side(client, make_user, course, db) -> None:
    """If I'm the SELLER on a listing, that conversation is NOT in my
    inquiries — it belongs in /my-listings instead.
    """
    me = client.current_user
    buyer = make_user(email="buyer@student.uaustin.org")
    my_listing = Listing(
        id=uuid.uuid4(),
        seller_id=me.id,
        course_id=course.id,
        book_title="Republic",
        book_author="Plato",
        condition="good",
        price_cents=1500,
        description="",
    )
    db.add(my_listing)
    db.commit()
    # The buyer contacts me about it.
    client.set_user(buyer)
    client.post(f"/api/listings/{my_listing.id}/contact")

    # Back to me — that conversation is seller-side, not in my inquiries.
    client.set_user(me)
    rows = client.get("/api/me/inquiries").json()
    assert rows == []


def test_inquiries_includes_unread_count(client, make_user, course, db) -> None:
    me = client.current_user
    seller = make_user(email="seller@student.uaustin.org")
    listing = Listing(
        id=uuid.uuid4(),
        seller_id=seller.id,
        course_id=course.id,
        book_title="Republic",
        book_author="Plato",
        condition="good",
        price_cents=1500,
        description="",
    )
    db.add(listing)
    db.commit()

    convo_id = client.post(f"/api/listings/{listing.id}/contact").json()["id"]
    # Seller replies twice.
    client.set_user(seller)
    client.post(f"/api/conversations/{convo_id}/messages", json={"body": "hi"})
    client.post(f"/api/conversations/{convo_id}/messages", json={"body": "still here"})

    client.set_user(me)
    rows = client.get("/api/me/inquiries").json()
    assert len(rows) == 1
    assert rows[0]["unread_count"] == 2


def test_inquiries_ordered_by_recent_activity(client, make_user, course, db) -> None:
    me = client.current_user
    seller_a = make_user(email="a@student.uaustin.org", display_name="A")
    seller_b = make_user(email="b@student.uaustin.org", display_name="B")

    lst_a = Listing(
        id=uuid.uuid4(),
        seller_id=seller_a.id,
        course_id=course.id,
        book_title="Republic",
        book_author="Plato",
        condition="good",
        price_cents=1500,
        description="",
    )
    lst_b = Listing(
        id=uuid.uuid4(),
        seller_id=seller_b.id,
        course_id=course.id,
        book_title="Meno",
        book_author="Plato",
        condition="good",
        price_cents=1200,
        description="",
    )
    db.add_all([lst_a, lst_b])
    db.commit()

    # Open A first, then B, then send a message in A. A should be most recent.
    conv_a = client.post(f"/api/listings/{lst_a.id}/contact").json()["id"]
    client.post(f"/api/listings/{lst_b.id}/contact")
    client.post(f"/api/conversations/{conv_a}/messages", json={"body": "ping"})

    rows = client.get("/api/me/inquiries").json()
    assert rows[0]["listing"]["book_title"] == "Republic"
    assert rows[1]["listing"]["book_title"] == "Meno"


def test_inquiries_requires_auth(anon_client) -> None:
    r = anon_client.get("/api/me/inquiries")
    assert r.status_code == 401
