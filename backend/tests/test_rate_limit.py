"""Tests for the message-send rate limiter."""
import uuid

import pytest
from sqlalchemy.orm import Session

from app.models import Course, Listing
from app.rate_limit import MESSAGE_RATE_LIMIT


@pytest.fixture()
def seller_with_listing(db: Session, make_user):
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


def test_rate_limit_blocks_after_threshold(client, seller_with_listing) -> None:
    """The Nth+1 message in a 60-second window from the same user gets
    429. Earlier ones go through.
    """
    _seller, listing = seller_with_listing
    conv_id = client.post(f"/api/listings/{listing.id}/contact").json()["id"]

    # First MESSAGE_RATE_LIMIT sends all succeed.
    for i in range(MESSAGE_RATE_LIMIT):
        r = client.post(
            f"/api/conversations/{conv_id}/messages",
            json={"body": f"msg {i}"},
        )
        assert r.status_code == 201, f"send {i} unexpectedly blocked: {r.text}"

    # The next one hits the limit.
    r = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"body": "over the limit"},
    )
    assert r.status_code == 429
    # Retry-After header is set so clients can back off intelligently.
    assert "Retry-After" in r.headers
    assert int(r.headers["Retry-After"]) >= 1


def test_rate_limit_is_per_user(client, seller_with_listing, make_user) -> None:
    """User A flooding messages doesn't block user B from sending."""
    seller, listing = seller_with_listing
    conv_id = client.post(f"/api/listings/{listing.id}/contact").json()["id"]

    # Buyer (current_user) saturates the limit.
    for i in range(MESSAGE_RATE_LIMIT):
        client.post(
            f"/api/conversations/{conv_id}/messages",
            json={"body": f"buyer msg {i}"},
        )

    # Swap to the seller — they share the conversation but have their
    # own rate-limit bucket, so their first send works.
    client.set_user(seller)
    r = client.post(
        f"/api/conversations/{conv_id}/messages",
        json={"body": "seller reply"},
    )
    assert r.status_code == 201, r.text
