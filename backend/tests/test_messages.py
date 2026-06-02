import uuid

import pytest
from sqlalchemy.orm import Session

from app.models import Course, Listing


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


def test_contact_creates_conversation(client, seller_with_listing) -> None:
    _seller, listing = seller_with_listing
    r = client.post(f"/api/listings/{listing.id}/contact")
    assert r.status_code == 201
    body = r.json()
    assert body["buyer"]["id"] == client.current_user.id
    assert body["listing"]["id"] == str(listing.id)


def test_contact_is_idempotent(client, seller_with_listing) -> None:
    _seller, listing = seller_with_listing
    a = client.post(f"/api/listings/{listing.id}/contact").json()
    b = client.post(f"/api/listings/{listing.id}/contact").json()
    assert a["id"] == b["id"]


def test_seller_cannot_contact_own_listing(client, db: Session) -> None:
    course = Course(id=uuid.uuid4(), code="PHIL 101", title="Intro to Philosophy")
    db.add(course)
    db.flush()
    listing = Listing(
        id=uuid.uuid4(),
        seller_id=client.current_user.id,
        course_id=course.id,
        title="Republic",
        author="Plato",
        condition="good",
        price_cents=1500,
        description="",
    )
    db.add(listing)
    db.commit()

    r = client.post(f"/api/listings/{listing.id}/contact")
    assert r.status_code == 400


def test_outsider_cannot_read_thread(client, seller_with_listing, make_user) -> None:
    _seller, listing = seller_with_listing
    # Buyer creates the conversation
    conv_id = client.post(f"/api/listings/{listing.id}/contact").json()["id"]
    client.post(f"/api/conversations/{conv_id}/messages", json={"body": "Hi"})

    outsider = make_user(email="outsider@student.uaustin.org")
    client.set_user(outsider)

    r = client.get(f"/api/conversations/{conv_id}/messages")
    assert r.status_code == 403
