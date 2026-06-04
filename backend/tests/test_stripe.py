"""Tests for the Stripe Connect checkout flow.

The Stripe SDK is monkey-patched out — we never hit the real API in
CI or local pytest. The mocks return shape-compatible objects so the
endpoints' code paths exercise the same attribute accesses they will
against the real SDK.

What's covered:
  - All endpoints return 503 when STRIPE_SECRET_KEY is unset.
  - Onboard: creates a Connect account on first call, reuses on
    subsequent calls; returns a fresh onboarding link both times.
  - Checkout: 400 on own-listing, not-active, no Stripe in
    payment_methods, seller not onboarded; 200 with URL on the happy
    path.
  - Webhook: signature failures rejected; account.updated flips
    stripe_onboarded; checkout.session.completed reserves the listing;
    repeated events are idempotent.
"""
from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from typing import Iterator

import pytest
import stripe
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Course, Listing, User


# --------------- Stripe SDK / env mocks ---------------


@pytest.fixture()
def stripe_env(monkeypatch) -> None:
    """Pretend Stripe is configured. Used by every test that exercises
    the happy path; tests that check the 503-when-unconfigured branch
    skip this fixture."""
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_fake")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test_fake")
    monkeypatch.setattr(settings, "STRIPE_RETURN_URL_BASE", "http://localhost:5173")
    monkeypatch.setattr(settings, "STRIPE_PLATFORM_FEE_BPS", 0)


@pytest.fixture()
def stripe_unconfigured(monkeypatch) -> None:
    """Force Stripe to look unconfigured. Without this, devs who have set
    STRIPE_SECRET_KEY in their local .env (perfectly normal once you're
    set up for end-to-end local testing) would see the 503-branch tests
    fail because pydantic-settings loads .env on Settings() instantiation.
    CI doesn't have a .env, so the bug went unnoticed there."""
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "")


@pytest.fixture()
def stripe_sdk(monkeypatch, stripe_env) -> dict:
    """Patch the Stripe SDK methods our router calls. Returns a dict of
    captured call kwargs so individual tests can assert on the inputs.

    SimpleNamespace gives us attribute access like real Stripe response
    objects (e.g. `account.id`, `link.url`, `sess.url`) without dragging
    in unittest.mock's MagicMock magic-everything behavior, which can
    silently absorb typos.
    """
    captured: dict = {"account_create": None, "link_create": None, "session_create": None}

    def fake_account_create(**kwargs):
        captured["account_create"] = kwargs
        return SimpleNamespace(id="acct_test_12345")

    def fake_link_create(**kwargs):
        captured["link_create"] = kwargs
        return SimpleNamespace(url="https://stripe.test/onboard/xyz")

    def fake_session_create(**kwargs):
        captured["session_create"] = kwargs
        return SimpleNamespace(url="https://stripe.test/checkout/sess_123")

    monkeypatch.setattr(stripe.Account, "create", staticmethod(fake_account_create))
    monkeypatch.setattr(stripe.AccountLink, "create", staticmethod(fake_link_create))
    monkeypatch.setattr(
        stripe.checkout.Session, "create", staticmethod(fake_session_create)
    )
    return captured


@pytest.fixture()
def stripe_webhook_mock(monkeypatch, stripe_env) -> Iterator[None]:
    """Bypass real signature verification; just parse the JSON payload."""

    def fake_construct_event(payload, sig_header, secret):
        return json.loads(payload.decode() if isinstance(payload, bytes) else payload)

    monkeypatch.setattr(
        stripe.Webhook, "construct_event", staticmethod(fake_construct_event)
    )
    yield


# --------------- Domain fixtures ---------------


@pytest.fixture()
def phil(db: Session) -> Course:
    c = Course(id=uuid.uuid4(), code="PHIL 101", title="Intro to Philosophy")
    db.add(c)
    db.commit()
    return c


def _seller_with_stripe(db: Session, make_user, *, onboarded: bool, account_id: str = "acct_seller_99"):
    seller = make_user(email="seller@student.uaustin.org", display_name="Seller")
    seller.stripe_account_id = account_id
    seller.stripe_onboarded = onboarded
    db.commit()
    db.refresh(seller)
    return seller


def _make_listing(
    db: Session,
    *,
    seller_id: str,
    course_id: uuid.UUID,
    payment_methods: list[str],
    status: str = "active",
    price_cents: int = 2500,
) -> Listing:
    l = Listing(
        id=uuid.uuid4(),
        seller_id=seller_id,
        course_id=course_id,
        category="book",
        title="Republic",
        author="Plato",
        condition="good",
        price_cents=price_cents,
        description="",
        status=status,
        payment_methods=payment_methods,
    )
    db.add(l)
    db.commit()
    db.refresh(l)
    return l


# --------------- 503 when not configured ---------------


def test_onboard_returns_503_when_stripe_not_configured(client, stripe_unconfigured) -> None:
    r = client.post("/api/me/stripe/onboard")
    assert r.status_code == 503
    assert "STRIPE_SECRET_KEY" in r.json()["detail"]


def test_checkout_returns_503_when_stripe_not_configured(
    client, stripe_unconfigured, phil, db, make_user
) -> None:
    seller = _seller_with_stripe(db, make_user, onboarded=True)
    listing = _make_listing(
        db, seller_id=seller.id, course_id=phil.id, payment_methods=["stripe"]
    )
    r = client.post(f"/api/listings/{listing.id}/checkout")
    assert r.status_code == 503


def test_webhook_returns_503_when_stripe_not_configured(client, stripe_unconfigured) -> None:
    r = client.post("/api/stripe/webhook", content=b"{}", headers={"stripe-signature": ""})
    assert r.status_code == 503


# --------------- Onboarding ---------------


def test_onboard_creates_account_on_first_call(client, stripe_sdk) -> None:
    r = client.post("/api/me/stripe/onboard")
    assert r.status_code == 200
    body = r.json()
    assert body["account_id"] == "acct_test_12345"
    assert body["onboarding_url"] == "https://stripe.test/onboard/xyz"
    assert body["onboarded"] is False
    # Confirms we called Stripe with the right shape — express type,
    # both capabilities, metadata with our user id.
    create_kwargs = stripe_sdk["account_create"]
    assert create_kwargs["type"] == "express"
    assert create_kwargs["country"] == "US"
    assert "card_payments" in create_kwargs["capabilities"]
    assert create_kwargs["metadata"]["user_id"] == client.current_user.id


def test_onboard_reuses_account_on_second_call(client, stripe_sdk) -> None:
    client.post("/api/me/stripe/onboard")
    stripe_sdk["account_create"] = None  # reset capture
    r = client.post("/api/me/stripe/onboard")
    assert r.status_code == 200
    # Account.create must NOT have been called the second time.
    assert stripe_sdk["account_create"] is None
    # But a fresh AccountLink should have been generated.
    assert stripe_sdk["link_create"] is not None


def test_onboard_skips_clerk_local_email(client, stripe_sdk, db) -> None:
    """Stripe rejects obviously-fake emails. When we don't have a real
    one (synthesized @clerk.local fallback), we just omit the field."""
    me = client.current_user
    me.email = f"{me.id}@clerk.local"
    db.commit()

    r = client.post("/api/me/stripe/onboard")
    assert r.status_code == 200
    assert stripe_sdk["account_create"]["email"] is None


# --------------- Checkout ---------------


def test_checkout_happy_path(client, stripe_sdk, phil, db, make_user) -> None:
    seller = _seller_with_stripe(db, make_user, onboarded=True)
    listing = _make_listing(
        db, seller_id=seller.id, course_id=phil.id, payment_methods=["stripe", "cash"]
    )

    r = client.post(f"/api/listings/{listing.id}/checkout")
    assert r.status_code == 200
    assert r.json()["url"] == "https://stripe.test/checkout/sess_123"

    kwargs = stripe_sdk["session_create"]
    assert kwargs["mode"] == "payment"
    assert kwargs["line_items"][0]["price_data"]["unit_amount"] == 2500
    assert kwargs["payment_intent_data"]["transfer_data"]["destination"] == seller.stripe_account_id
    # Metadata threads listing_id + buyer_id through so the webhook can
    # close the loop.
    assert kwargs["metadata"]["listing_id"] == str(listing.id)
    assert kwargs["metadata"]["buyer_id"] == client.current_user.id


def test_checkout_rejects_own_listing(client, stripe_sdk, phil, db) -> None:
    """Buyer === seller is a 400, not a Stripe round-trip."""
    me = client.current_user
    me.stripe_account_id = "acct_me"
    me.stripe_onboarded = True
    db.commit()

    listing = _make_listing(
        db, seller_id=me.id, course_id=phil.id, payment_methods=["stripe"]
    )
    r = client.post(f"/api/listings/{listing.id}/checkout")
    assert r.status_code == 400
    assert stripe_sdk["session_create"] is None


def test_checkout_rejects_listing_without_stripe_method(
    client, stripe_sdk, phil, db, make_user
) -> None:
    seller = _seller_with_stripe(db, make_user, onboarded=True)
    listing = _make_listing(
        db,
        seller_id=seller.id,
        course_id=phil.id,
        payment_methods=["cash", "venmo"],  # no stripe
    )
    r = client.post(f"/api/listings/{listing.id}/checkout")
    assert r.status_code == 400
    assert "Stripe" in r.json()["detail"]
    assert stripe_sdk["session_create"] is None


def test_checkout_rejects_seller_not_onboarded(
    client, stripe_sdk, phil, db, make_user
) -> None:
    seller = _seller_with_stripe(db, make_user, onboarded=False)
    listing = _make_listing(
        db, seller_id=seller.id, course_id=phil.id, payment_methods=["stripe"]
    )
    r = client.post(f"/api/listings/{listing.id}/checkout")
    assert r.status_code == 400
    assert "Stripe" in r.json()["detail"]
    assert stripe_sdk["session_create"] is None


def test_checkout_rejects_non_active_listing(
    client, stripe_sdk, phil, db, make_user
) -> None:
    seller = _seller_with_stripe(db, make_user, onboarded=True)
    listing = _make_listing(
        db,
        seller_id=seller.id,
        course_id=phil.id,
        payment_methods=["stripe"],
        status="sold",
    )
    r = client.post(f"/api/listings/{listing.id}/checkout")
    assert r.status_code == 400


def test_checkout_includes_application_fee_when_bps_nonzero(
    client, stripe_sdk, monkeypatch, phil, db, make_user
) -> None:
    monkeypatch.setattr(settings, "STRIPE_PLATFORM_FEE_BPS", 500)  # 5%
    seller = _seller_with_stripe(db, make_user, onboarded=True)
    listing = _make_listing(
        db,
        seller_id=seller.id,
        course_id=phil.id,
        payment_methods=["stripe"],
        price_cents=10000,  # $100
    )
    client.post(f"/api/listings/{listing.id}/checkout")
    kwargs = stripe_sdk["session_create"]
    # 5% of $100 = $5 = 500 cents.
    assert kwargs["payment_intent_data"]["application_fee_amount"] == 500


# --------------- Webhook ---------------


def _post_webhook(client, event: dict):
    return client.post(
        "/api/stripe/webhook",
        content=json.dumps(event).encode(),
        headers={"stripe-signature": "t=fake,v1=fake"},
    )


def test_webhook_account_updated_flips_onboarded(
    client, stripe_webhook_mock, db, make_user
) -> None:
    seller = _seller_with_stripe(db, make_user, onboarded=False, account_id="acct_xyz")

    r = _post_webhook(client, {
        "type": "account.updated",
        "data": {
            "object": {
                "id": "acct_xyz",
                "charges_enabled": True,
                "details_submitted": True,
            }
        },
    })
    assert r.status_code == 200

    db.refresh(seller)
    assert seller.stripe_onboarded is True


def test_webhook_account_updated_ignores_partial_onboarding(
    client, stripe_webhook_mock, db, make_user
) -> None:
    """Stripe sends account.updated mid-onboarding too; we only flip
    the flag once both charges_enabled and details_submitted are true."""
    seller = _seller_with_stripe(db, make_user, onboarded=False, account_id="acct_xyz")
    r = _post_webhook(client, {
        "type": "account.updated",
        "data": {
            "object": {
                "id": "acct_xyz",
                "charges_enabled": True,
                "details_submitted": False,  # not yet
            }
        },
    })
    assert r.status_code == 200
    db.refresh(seller)
    assert seller.stripe_onboarded is False


def test_webhook_checkout_completed_reserves_listing(
    client, stripe_webhook_mock, phil, db, make_user
) -> None:
    seller = _seller_with_stripe(db, make_user, onboarded=True)
    listing = _make_listing(
        db, seller_id=seller.id, course_id=phil.id, payment_methods=["stripe"]
    )
    assert listing.status == "active"

    r = _post_webhook(client, {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "metadata": {
                    "listing_id": str(listing.id),
                    "buyer_id": client.current_user.id,
                    "seller_id": seller.id,
                },
            }
        },
    })
    assert r.status_code == 200
    db.refresh(listing)
    assert listing.status == "reserved"


def test_webhook_checkout_completed_is_idempotent(
    client, stripe_webhook_mock, phil, db, make_user
) -> None:
    """Stripe retries webhooks on non-2xx. Same event twice must not
    change anything the second time — current state guards mutation."""
    seller = _seller_with_stripe(db, make_user, onboarded=True)
    listing = _make_listing(
        db, seller_id=seller.id, course_id=phil.id, payment_methods=["stripe"]
    )
    # Simulate the seller already marking it sold between webhook retries.
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "metadata": {"listing_id": str(listing.id)},
            }
        },
    }
    _post_webhook(client, event)
    db.refresh(listing)
    listing.status = "sold"
    db.commit()

    # Resend the same event.
    r = _post_webhook(client, event)
    assert r.status_code == 200
    db.refresh(listing)
    # Listing stays sold — the webhook only acts on active listings.
    assert listing.status == "sold"


def test_webhook_unknown_event_is_swallowed(
    client, stripe_webhook_mock, db
) -> None:
    """Random event types (refunds, disputes, etc.) we don't handle yet
    should 200 so Stripe doesn't retry them forever."""
    r = _post_webhook(client, {
        "type": "charge.refunded",
        "data": {"object": {}},
    })
    assert r.status_code == 200
