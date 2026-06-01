"""Tests for unread-count and mark-conversation-read.

The unread badge in the top nav and the auto-mark-read when opening a
conversation. Both reach into the same `messages.read_at` column.
"""
import uuid

import pytest
from sqlalchemy.orm import Session

from app.models import Conversation, Course, Listing, Message


@pytest.fixture()
def seller_and_listing(db: Session, make_user):
    seller = make_user(email="seller@student.uaustin.org", display_name="Seller")
    course = Course(id=uuid.uuid4(), code="PHIL 101", title="Intro to Philosophy")
    db.add(course)
    db.flush()
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
    db.refresh(listing)
    return seller, listing


def test_unread_count_starts_at_zero(client) -> None:
    r = client.get("/api/me/unread-count")
    assert r.status_code == 200
    assert r.json() == {"count": 0}


def test_unread_count_includes_incoming_message(client, seller_and_listing, db) -> None:
    seller, listing = seller_and_listing
    # Buyer (current_user) creates a conversation
    conv_id = client.post(f"/api/listings/{listing.id}/contact").json()["id"]

    # Seller sends a message TO the buyer (current_user). Simulate via direct DB
    # insert so we don't have to swap clients.
    msg = Message(
        id=uuid.uuid4(),
        conversation_id=uuid.UUID(conv_id),
        sender_id=seller.id,
        body="Still available?",
        read_at=None,
    )
    db.add(msg)
    db.commit()

    r = client.get("/api/me/unread-count")
    assert r.json() == {"count": 1}


def test_unread_count_excludes_my_own_outgoing(client, seller_and_listing) -> None:
    _seller, listing = seller_and_listing
    conv_id = client.post(f"/api/listings/{listing.id}/contact").json()["id"]
    # Buyer (current_user) sends to seller. That's outgoing — shouldn't count
    # against the buyer's unread.
    client.post(f"/api/conversations/{conv_id}/messages", json={"body": "Hi"})

    r = client.get("/api/me/unread-count")
    assert r.json() == {"count": 0}


def test_unread_count_excludes_conversations_im_not_in(client, seller_and_listing, make_user, db) -> None:
    seller, listing = seller_and_listing
    # A third party creates a conversation with the seller and sends a message.
    third = make_user(email="third@student.uaustin.org")
    conv = Conversation(
        id=uuid.uuid4(),
        listing_id=listing.id,
        buyer_id=third.id,
        other_user_id=seller.id,
    )
    db.add(conv)
    db.flush()
    db.add(
        Message(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            sender_id=third.id,
            body="hey",
            read_at=None,
        )
    )
    db.commit()

    # current_user (a buyer in a DIFFERENT scenario, but here neither buyer nor seller)
    # should see unread_count = 0 for this conversation.
    r = client.get("/api/me/unread-count")
    assert r.json() == {"count": 0}


def test_mark_read_clears_incoming_unread(client, seller_and_listing, db) -> None:
    seller, listing = seller_and_listing
    conv_id = client.post(f"/api/listings/{listing.id}/contact").json()["id"]

    # Two incoming messages from seller, one outgoing from buyer.
    db.add_all(
        [
            Message(
                id=uuid.uuid4(),
                conversation_id=uuid.UUID(conv_id),
                sender_id=seller.id,
                body="A",
                read_at=None,
            ),
            Message(
                id=uuid.uuid4(),
                conversation_id=uuid.UUID(conv_id),
                sender_id=seller.id,
                body="B",
                read_at=None,
            ),
        ]
    )
    db.commit()
    client.post(f"/api/conversations/{conv_id}/messages", json={"body": "reply"})

    # Before: 2 unread incoming
    assert client.get("/api/me/unread-count").json()["count"] == 2

    # Mark read
    r = client.post(f"/api/conversations/{conv_id}/read")
    assert r.status_code == 200
    assert r.json() == {"marked_read": 2}

    # After: 0
    assert client.get("/api/me/unread-count").json()["count"] == 0


def test_mark_read_is_idempotent(client, seller_and_listing) -> None:
    _seller, listing = seller_and_listing
    conv_id = client.post(f"/api/listings/{listing.id}/contact").json()["id"]
    # No messages → marking read does nothing, doesn't error.
    a = client.post(f"/api/conversations/{conv_id}/read").json()
    b = client.post(f"/api/conversations/{conv_id}/read").json()
    assert a == {"marked_read": 0}
    assert b == {"marked_read": 0}


def test_mark_read_requires_membership(client, seller_and_listing, make_user) -> None:
    _seller, listing = seller_and_listing
    conv_id = client.post(f"/api/listings/{listing.id}/contact").json()["id"]
    outsider = make_user(email="outsider@student.uaustin.org")
    client.set_user(outsider)

    r = client.post(f"/api/conversations/{conv_id}/read")
    assert r.status_code == 403


def test_unread_count_requires_auth(anon_client) -> None:
    r = anon_client.get("/api/me/unread-count")
    assert r.status_code == 401
