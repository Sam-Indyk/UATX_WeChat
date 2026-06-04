"""Tests for the public seller-profile endpoint at GET /api/users/{user_id}."""
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


def _post_listing(client, course_id, **overrides) -> str:
    """Helper: create a listing as the current client user and return its id."""
    base = {
        "course_id": str(course_id),
        "title": "Republic",
        "author": "Plato",
        "edition": None,
        "condition": "good",
        "price_cents": 1500,
        "description": "",
    }
    base.update(overrides)
    r = client.post("/api/listings", json=base)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_get_profile_returns_user_and_active_listings(client, course, make_user) -> None:
    seller = make_user(display_name="Seller Sam")
    client.set_user(seller)
    _post_listing(client, course.id, title="Republic")
    _post_listing(client, course.id, title="Phaedrus")

    # Switch to a viewer — profile is the same for anyone.
    viewer = make_user(email="viewer@student.uaustin.org")
    client.set_user(viewer)
    r = client.get(f"/api/users/{seller.id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == seller.id
    assert body["display_name"] == "Seller Sam"
    titles = sorted(l["title"] for l in body["active_listings"])
    assert titles == ["Phaedrus", "Republic"]


def test_profile_excludes_non_active_listings(client, course, make_user, db: Session) -> None:
    """Reserved / sold / withdrawn listings shouldn't appear on the public
    profile — they aren't buyable, and surfacing them just clutters the page.
    """
    seller = make_user(display_name="S")
    client.set_user(seller)
    active_id = _post_listing(client, course.id, title="Active")
    sold_id = _post_listing(client, course.id, title="Sold")
    reserved_id = _post_listing(client, course.id, title="Reserved")

    # Flip statuses directly — the PATCH endpoint is exercised elsewhere.
    db.get(Listing, uuid.UUID(sold_id)).status = "sold"
    db.get(Listing, uuid.UUID(reserved_id)).status = "reserved"
    db.commit()

    r = client.get(f"/api/users/{seller.id}")
    assert r.status_code == 200
    body = r.json()
    assert [l["id"] for l in body["active_listings"]] == [active_id]


def test_profile_only_includes_target_users_listings(client, course, make_user) -> None:
    """Cross-user isolation: viewing user A shouldn't return user B's items."""
    seller_a = make_user(display_name="A", email="a@student.uaustin.org")
    client.set_user(seller_a)
    a_listing = _post_listing(client, course.id, title="A's book")

    seller_b = make_user(display_name="B", email="b@student.uaustin.org")
    client.set_user(seller_b)
    _post_listing(client, course.id, title="B's book")

    r = client.get(f"/api/users/{seller_a.id}")
    body = r.json()
    assert len(body["active_listings"]) == 1
    assert body["active_listings"][0]["id"] == a_listing


def test_profile_404_for_unknown_user(client) -> None:
    r = client.get("/api/users/user_doesnotexist")
    assert r.status_code == 404


def test_profile_omits_email_field(client, course, make_user) -> None:
    """Email is intentionally not in PublicUserOut — only display_name + avatar."""
    seller = make_user(email="seller@student.uaustin.org", display_name="Seller")
    client.set_user(seller)
    r = client.get(f"/api/users/{seller.id}")
    assert r.status_code == 200
    body = r.json()
    assert "email" not in body
    # stripe_onboarded is also internal — don't leak it on the public profile.
    assert "stripe_onboarded" not in body


def test_profile_requires_auth(anon_client, make_user) -> None:
    seller = make_user()
    r = anon_client.get(f"/api/users/{seller.id}")
    assert r.status_code == 401
