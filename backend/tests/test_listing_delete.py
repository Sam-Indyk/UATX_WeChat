"""Tests for DELETE /api/listings/{id} — the "Take down" action.

Hard-deletes the listing, cascades to conversations + messages, and
best-effort removes the image from Supabase Storage.
"""
import uuid

import pytest
from sqlalchemy.orm import Session

from app.models import Course, Conversation, Listing, Message
from app.routers import listings as listings_router


@pytest.fixture(autouse=True)
def fake_image_delete(monkeypatch):
    """Capture delete_stored_image calls so we can assert on them
    without hitting Supabase Storage from CI.
    """
    calls = []

    def _fake(url):
        calls.append(url)

    monkeypatch.setattr(listings_router, "delete_stored_image", _fake)
    yield calls


@pytest.fixture()
def my_listing(client, db: Session) -> Listing:
    course = Course(id=uuid.uuid4(), code="PHIL 101", title="Intro to Philosophy")
    db.add(course)
    db.flush()
    listing = Listing(
        id=uuid.uuid4(),
        seller_id=client.current_user.id,
        course_id=course.id,
        category="book",
        title="Republic",
        author="Plato",
        condition="good",
        price_cents=1500,
        description="",
        image_url="https://fake-storage/listings/abc/photo.png",
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def test_take_down_deletes_listing(client, my_listing, db: Session) -> None:
    r = client.delete(f"/api/listings/{my_listing.id}")
    assert r.status_code == 204
    # Row is gone.
    assert db.get(Listing, my_listing.id) is None


def test_take_down_calls_storage_cleanup(client, my_listing, fake_image_delete) -> None:
    client.delete(f"/api/listings/{my_listing.id}")
    assert fake_image_delete == ["https://fake-storage/listings/abc/photo.png"]


def test_take_down_cascades_to_conversations(
    client, my_listing, make_user, db: Session
) -> None:
    """Buyers who messaged about this listing lose their conversation
    when the seller takes it down. Cascade is configured at the schema
    level (conversations.listing_id ON DELETE CASCADE) — we just verify
    it actually fires.
    """
    buyer = make_user(email="buyer@student.uaustin.org")
    # Buyer creates a conversation about the listing.
    client.set_user(buyer)
    conv_id = client.post(f"/api/listings/{my_listing.id}/contact").json()["id"]
    client.post(f"/api/conversations/{conv_id}/messages", json={"body": "interested!"})

    # Seller takes it down.
    client.set_user(my_listing.seller_id)  # set_user takes a User, not a string
    # ↑ wrong call shape — use the seller User from make_user/fixtures.
    # Easier: just re-open as the original current_user that owns the
    # listing (set up via the `my_listing` fixture which used
    # client.current_user.id as the seller).
    # Reset to a user that IS the seller:
    from app.models import User as UserModel

    seller = db.get(UserModel, my_listing.seller_id)
    assert seller is not None
    client.set_user(seller)

    r = client.delete(f"/api/listings/{my_listing.id}")
    assert r.status_code == 204
    # Conversation and its messages should be gone.
    assert db.get(Conversation, uuid.UUID(conv_id)) is None
    msgs = db.query(Message).filter_by(conversation_id=uuid.UUID(conv_id)).count()
    assert msgs == 0


def test_take_down_only_seller(client, my_listing, make_user) -> None:
    other = make_user(email="other@student.uaustin.org")
    client.set_user(other)
    r = client.delete(f"/api/listings/{my_listing.id}")
    assert r.status_code == 403


def test_take_down_unknown_listing_404(client) -> None:
    r = client.delete(f"/api/listings/{uuid.uuid4()}")
    assert r.status_code == 404


def test_take_down_requires_auth(anon_client, db: Session, make_user) -> None:
    seller = make_user()
    course = Course(id=uuid.uuid4(), code="PHIL 101", title="Intro to Philosophy")
    db.add(course)
    db.flush()
    listing = Listing(
        id=uuid.uuid4(),
        seller_id=seller.id,
        course_id=course.id,
        category="book",
        title="Republic",
        author="Plato",
        condition="good",
        price_cents=1500,
        description="",
    )
    db.add(listing)
    db.commit()
    r = anon_client.delete(f"/api/listings/{listing.id}")
    assert r.status_code == 401


def test_my_listings_excludes_withdrawn(client, my_listing) -> None:
    """Legacy rows that are still status='withdrawn' (from before the
    take-down-deletes change) shouldn't show in the seller's My Listings."""
    client.patch(f"/api/listings/{my_listing.id}", json={"status": "withdrawn"})
    rows = client.get("/api/me/listings").json()
    ids = [r["id"] for r in rows]
    assert str(my_listing.id) not in ids
