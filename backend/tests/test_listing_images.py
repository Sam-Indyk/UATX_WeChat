"""Tests for the listing-image upload endpoint.

We don't hit Supabase Storage from CI — we monkeypatch the uploader so
the endpoint contract is exercised without needing real credentials.
"""
import io
import uuid

import pytest
from sqlalchemy.orm import Session

from app.models import Course, Listing
from app.routers import listings as listings_router


@pytest.fixture(autouse=True)
def fake_uploader(monkeypatch):
    """Replace the real Supabase uploader with a deterministic stub for
    every test in this file. Returns a fake public URL keyed by listing id
    so assertions can pin behavior without a real bucket.
    """
    def _fake(*, listing_id, content_type: str, data: bytes) -> str:
        return f"https://fake-storage/listings/{listing_id}/img.{content_type.split('/')[-1]}"

    monkeypatch.setattr(listings_router, "upload_listing_image", _fake)
    yield _fake


@pytest.fixture()
def my_listing(client, db: Session) -> Listing:
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
    db.refresh(listing)
    return listing


def _png_bytes() -> bytes:
    # A tiny valid PNG header is enough — endpoint doesn't decode the image.
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


def test_upload_image_happy_path(client, my_listing) -> None:
    r = client.post(
        f"/api/listings/{my_listing.id}/image",
        files={"file": ("book.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["image_url"].startswith("https://fake-storage/listings/")
    assert body["image_url"].endswith(".png")

    # Subsequent GET on the listing reflects the URL.
    r2 = client.get(f"/api/listings/{my_listing.id}")
    assert r2.json()["image_url"] == body["image_url"]


def test_upload_image_rejects_non_image_mime(client, my_listing) -> None:
    r = client.post(
        f"/api/listings/{my_listing.id}/image",
        files={"file": ("evil.exe", b"MZ" + b"\x00" * 100, "application/octet-stream")},
    )
    assert r.status_code == 415


def test_upload_image_rejects_oversized(client, my_listing) -> None:
    big = b"\x89PNG\r\n\x1a\n" + b"\x00" * (5 * 1024 * 1024 + 1)
    r = client.post(
        f"/api/listings/{my_listing.id}/image",
        files={"file": ("big.png", big, "image/png")},
    )
    assert r.status_code == 413


def test_upload_image_only_seller(client, my_listing, make_user) -> None:
    other = make_user(email="other@student.uaustin.org")
    client.set_user(other)
    r = client.post(
        f"/api/listings/{my_listing.id}/image",
        files={"file": ("book.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 403


def test_upload_image_listing_must_exist(client) -> None:
    fake_id = uuid.uuid4()
    r = client.post(
        f"/api/listings/{fake_id}/image",
        files={"file": ("book.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 404


def test_upload_image_requires_auth(anon_client, db: Session, make_user) -> None:
    # Build the listing without going through `client`, otherwise its
    # require_user override leaks into anon_client and we'd get a 200.
    seller = make_user()
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

    r = anon_client.post(
        f"/api/listings/{listing.id}/image",
        files={"file": ("book.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 401


def test_listing_response_includes_image_url_when_unset(client, my_listing) -> None:
    r = client.get(f"/api/listings/{my_listing.id}")
    assert r.status_code == 200
    body = r.json()
    assert "image_url" in body
    assert body["image_url"] is None
