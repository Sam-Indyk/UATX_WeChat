"""Cross-cutting authorization + input-validation safety tests.

These cover boundaries that are easy to miss when adding endpoints — and
boundaries that would be embarrassing to leak in prod. Each test asserts
a refusal (403 / 404 / 422 / no-data-returned), not a happy path.
"""
import uuid

import pytest
from sqlalchemy.orm import Session

from app.models import Conversation, Course, Listing


@pytest.fixture()
def seller_with_listing(db: Session, make_user):
    """Same shape as test_messages.py's fixture — duplicated so this file
    stays self-contained. Cheap enough that the duplication isn't worth a
    shared conftest entry yet."""
    seller = make_user(email="seller@student.uaustin.org", display_name="Seller")
    course = Course(id=uuid.uuid4(), code="PHIL 101", title="Intro to Philosophy")
    db.add(course)
    db.flush()
    listing = Listing(
        id=uuid.uuid4(),
        seller_id=seller.id,
        course_id=course.id,
        title="Republic",
        author="Plato",
        condition="good",
        price_cents=1500,
        description="",
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return seller, listing


# --------------- Cross-user authorization ---------------


def test_outsider_cannot_send_message(client, seller_with_listing, make_user) -> None:
    """Mirror of test_outsider_cannot_read_thread, but for POST. The
    send-message endpoint must enforce conversation membership; without
    this an attacker who guesses (or scrapes) a conversation UUID could
    inject messages between two unrelated users.
    """
    _seller, listing = seller_with_listing
    # Buyer (current_user) starts the convo.
    conv_id = client.post(f"/api/listings/{listing.id}/contact").json()["id"]

    outsider = make_user(email="outsider@student.uaustin.org")
    client.set_user(outsider)

    r = client.post(f"/api/conversations/{conv_id}/messages", json={"body": "hi"})
    assert r.status_code == 403


def test_list_my_conversations_excludes_others(client, seller_with_listing, make_user) -> None:
    """Belt-and-suspenders: GET /api/conversations must not surface
    conversations the viewer isn't a party to. The query already filters
    on buyer_id/other_user_id, but if someone refactors the WHERE clause
    away this test screams.
    """
    seller, listing = seller_with_listing
    # Two unrelated users carry on their own conversation.
    other_a = make_user(email="alice@student.uaustin.org")
    client.set_user(other_a)
    client.post(f"/api/listings/{listing.id}/contact")

    # current_user (a third user) lists their conversations — should be empty.
    snoop = make_user(email="snoop@student.uaustin.org")
    client.set_user(snoop)
    r = client.get("/api/conversations")
    assert r.status_code == 200
    assert r.json() == []


# --------------- 404 paths (don't leak existence as a 500) ---------------


def test_send_message_to_unknown_conversation_404(client) -> None:
    r = client.post(
        f"/api/conversations/{uuid.uuid4()}/messages", json={"body": "hi"}
    )
    assert r.status_code == 404


def test_mark_read_on_unknown_conversation_404(client) -> None:
    r = client.post(f"/api/conversations/{uuid.uuid4()}/read")
    assert r.status_code == 404


def test_contact_unknown_listing_404(client) -> None:
    r = client.post(f"/api/listings/{uuid.uuid4()}/contact")
    assert r.status_code == 404


# --------------- Pydantic input validation on messages ---------------


def test_empty_message_body_rejected(client, seller_with_listing) -> None:
    """MessageIn enforces min_length=1 — an empty string would otherwise
    let users spam blank rows that look like glitches in the UI."""
    _seller, listing = seller_with_listing
    conv_id = client.post(f"/api/listings/{listing.id}/contact").json()["id"]

    r = client.post(f"/api/conversations/{conv_id}/messages", json={"body": ""})
    assert r.status_code == 422


def test_oversize_message_body_rejected(client, seller_with_listing) -> None:
    """max_length=2000 — keeps a runaway client from stuffing a megabyte
    of text into a single message row. 2001 chars trips the cap."""
    _seller, listing = seller_with_listing
    conv_id = client.post(f"/api/listings/{listing.id}/contact").json()["id"]

    r = client.post(
        f"/api/conversations/{conv_id}/messages", json={"body": "a" * 2001}
    )
    assert r.status_code == 422


# --------------- Listing input validation ---------------


def test_listing_price_over_cap_rejected(client, seller_with_listing) -> None:
    """price_cents has le=100_000_00 (= $100K). Without an upper cap a
    user typing a giant number would overflow Postgres INT4 and surface
    a 500 — the cap turns that into a clean 422. Regression guard for
    the "I typed a bunch of ones" bug Eitan reported."""
    _seller, listing = seller_with_listing
    r = client.post(
        "/api/listings",
        json={
            "course_id": str(listing.course_id),
            "title": "Eye-watering",
            "author": "Anon",
            "condition": "good",
            "price_cents": 10_000_000_01,  # $100,000.01 — one cent over the cap
        },
    )
    assert r.status_code == 422


def test_listing_negative_price_rejected(client, seller_with_listing) -> None:
    """price_cents has ge=0 — a negative price would pay the buyer, which
    is the kind of thing that goes viral on Twitter."""
    _seller, listing = seller_with_listing
    r = client.post(
        "/api/listings",
        json={
            "course_id": str(listing.course_id),
            "title": "Cheap book",
            "author": "Anon",
            "condition": "good",
            "price_cents": -100,
        },
    )
    assert r.status_code == 422


def test_listing_unknown_payment_method_rejected(client, seller_with_listing) -> None:
    """payment_methods is a Pydantic Literal — unknown values get a 422
    before they reach the DB's ARRAY column."""
    _seller, listing = seller_with_listing
    r = client.post(
        "/api/listings",
        json={
            "course_id": str(listing.course_id),
            "title": "Republic",
            "author": "Plato",
            "condition": "good",
            "price_cents": 1500,
            "payment_methods": ["bitcoin"],
        },
    )
    assert r.status_code == 422


def test_book_without_author_is_accepted(client, seller_with_listing) -> None:
    """Author is optional on book listings — some books are unattributed,
    compiled, or anonymous (lab manuals, classics, course readers). The
    Sell-a-book form lets the seller leave it blank, and the backend must
    accept that."""
    _seller, listing = seller_with_listing
    r = client.post(
        "/api/listings",
        json={
            "category": "book",
            "course_id": str(listing.course_id),
            "title": "Untitled",
            "condition": "good",
            "price_cents": 1500,
        },
    )
    assert r.status_code == 201
    assert r.json()["author"] is None
