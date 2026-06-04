"""Stripe Connect — sellers onboard, buyers check out, webhook closes the loop.

Three public endpoints:

  - ``POST /api/me/stripe/onboard``
      Create-or-fetch a Stripe Connect Express account for the signed-in
      user, then return a Stripe-hosted onboarding URL. Idempotent —
      calling it a second time just generates a fresh link against the
      same account.

  - ``POST /api/listings/{listing_id}/checkout``
      Buyer initiates a payment for someone else's active listing.
      Creates a Stripe Checkout Session on the seller's connected
      account (destination charge), returns the redirect URL. Rejects
      self-purchase, non-active listings, listings that don't have
      ``stripe`` in their accepted ``payment_methods``, and sellers
      who haven't finished onboarding.

  - ``POST /api/stripe/webhook``
      Stripe's async callbacks. Two events we care about for the demo:
      ``account.updated`` (flip ``stripe_onboarded=True`` once Stripe
      reports the seller can charge) and ``checkout.session.completed``
      (move the listing to ``reserved`` once the buyer paid).

Every endpoint returns 503 if ``STRIPE_SECRET_KEY`` isn't set, so the
app doesn't 500 in environments where Stripe was never configured.

The Checkout-redirect MVP deliberately stops short of a full
buyer→seller-confirm→funds-release state machine — see EITAN.md. We
hand-off to Stripe's hosted page for the payment UI, eat the redirect
back, and reserve the listing on webhook confirmation. The seller
still manually marks the listing 'sold' from /my-listings when the
handoff is done.
"""
from __future__ import annotations

import json
import logging
import uuid

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_user
from app.config import settings
from app.db import get_db
from app.models import Listing, User


router = APIRouter(tags=["stripe"])
logger = logging.getLogger(__name__)


# ---------- Response shapes ----------


class StripeOnboardOut(BaseModel):
    onboarding_url: str
    account_id: str
    onboarded: bool


class CheckoutOut(BaseModel):
    url: str


# ---------- Helpers ----------


def _require_stripe_configured() -> None:
    """Raise 503 if Stripe isn't set up on this environment. Sets the
    SDK's api_key on every call so a misconfigured restart can't leak
    a stale key from a previous run."""
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe isn't configured on this environment. Set STRIPE_SECRET_KEY.",
        )
    stripe.api_key = settings.STRIPE_SECRET_KEY


# ---------- Endpoints ----------


@router.post("/api/me/stripe/onboard", response_model=StripeOnboardOut)
def onboard_stripe(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> StripeOnboardOut:
    """Kick off (or resume) Stripe Connect onboarding for the signed-in
    user. Creates an Express account the first time, then issues a fresh
    onboarding link every call so refreshing the page in the middle of
    the flow always lands on a valid URL."""
    _require_stripe_configured()

    # Lazy account creation. Skip if we already have one stashed.
    if not user.stripe_account_id:
        # Stripe rejects synthesized clerk.local emails as obviously
        # fake; just omit the email field in that case and let the user
        # fill it in during onboarding.
        email = None if user.email.endswith("@clerk.local") else user.email
        account = stripe.Account.create(
            type="express",
            country="US",
            email=email,
            capabilities={
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
            metadata={"user_id": user.id},
        )
        user.stripe_account_id = account.id
        db.commit()
        db.refresh(user)

    link = stripe.AccountLink.create(
        account=user.stripe_account_id,
        refresh_url=f"{settings.STRIPE_RETURN_URL_BASE}/settings?stripe=refresh",
        return_url=f"{settings.STRIPE_RETURN_URL_BASE}/settings?stripe=return",
        type="account_onboarding",
    )

    return StripeOnboardOut(
        onboarding_url=link.url,
        account_id=user.stripe_account_id,
        onboarded=user.stripe_onboarded,
    )


@router.post("/api/listings/{listing_id}/checkout", response_model=CheckoutOut)
def create_checkout(
    listing_id: uuid.UUID,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> CheckoutOut:
    """Buyer-initiated Stripe Checkout for a listing.

    Returns the Stripe-hosted Checkout Session URL the frontend should
    redirect to. The actual reservation of the listing happens
    asynchronously when Stripe POSTs ``checkout.session.completed`` to
    the webhook — we *don't* mark anything reserved at this step
    because the user might bail at the Stripe page.
    """
    _require_stripe_configured()

    listing = db.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.seller_id == user.id:
        raise HTTPException(status_code=400, detail="Can't buy your own listing")
    if listing.status != "active":
        raise HTTPException(status_code=400, detail="Listing isn't available")
    if "stripe" not in (listing.payment_methods or []):
        raise HTTPException(
            status_code=400,
            detail="This seller doesn't accept Stripe payments on this listing.",
        )

    seller = db.get(User, listing.seller_id)
    if seller is None or not seller.stripe_account_id or not seller.stripe_onboarded:
        raise HTTPException(
            status_code=400,
            detail="Seller hasn't finished setting up Stripe payments yet.",
        )

    # Platform fee in cents. STRIPE_PLATFORM_FEE_BPS is in basis points
    # (1 bps = 0.01%), so price_cents * bps / 10000 gives cents. The
    # demo runs at 0 — we're not actually collecting money.
    fee_cents = (listing.price_cents * settings.STRIPE_PLATFORM_FEE_BPS) // 10000

    payment_intent_data: dict = {
        "transfer_data": {"destination": seller.stripe_account_id},
    }
    if fee_cents > 0:
        payment_intent_data["application_fee_amount"] = fee_cents

    sess = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": listing.price_cents,
                    # Stripe caps product name at 250 chars; truncate
                    # defensively even though our titles are <=200.
                    "product_data": {"name": listing.title[:120]},
                },
                "quantity": 1,
            }
        ],
        payment_intent_data=payment_intent_data,
        success_url=(
            f"{settings.STRIPE_RETURN_URL_BASE}/listings/{listing.id}?stripe=success"
        ),
        cancel_url=(
            f"{settings.STRIPE_RETURN_URL_BASE}/listings/{listing.id}?stripe=cancel"
        ),
        metadata={
            "listing_id": str(listing.id),
            "buyer_id": user.id,
            "seller_id": seller.id,
        },
    )
    return CheckoutOut(url=sess.url)


@router.post("/api/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(default="", alias="stripe-signature"),
    db: Session = Depends(get_db),
) -> dict:
    """Stripe's async callbacks.

    We verify the signature with ``STRIPE_WEBHOOK_SECRET`` and process
    two event types. Idempotency: re-sent events (Stripe retries on
    non-2xx) are safe because we check current state before mutating.

    Local dev: use ``stripe listen --forward-to localhost:8000/api/stripe/webhook``
    and copy the printed ``whsec_...`` to your ``.env``. Prod webhook
    secret comes from creating an endpoint in the Stripe dashboard.
    """
    _require_stripe_configured()

    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="STRIPE_WEBHOOK_SECRET not set — webhook can't verify signatures.",
        )

    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail=f"Invalid signature: {e}")
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")

    event_type = event["type"]

    if event_type == "account.updated":
        account = event["data"]["object"]
        # Stripe says the account is fully usable for charges once both
        # `details_submitted` and `charges_enabled` are true. Some test-
        # mode accounts skip parts of onboarding; this is the conservative
        # both-flags check.
        if account.get("charges_enabled") and account.get("details_submitted"):
            seller = db.execute(
                select(User).where(User.stripe_account_id == account["id"])
            ).scalar_one_or_none()
            if seller and not seller.stripe_onboarded:
                seller.stripe_onboarded = True
                db.commit()
                logger.info("Stripe: marked user %s as onboarded", seller.id)

    elif event_type == "checkout.session.completed":
        session = event["data"]["object"]
        listing_id_raw = (session.get("metadata") or {}).get("listing_id")
        if listing_id_raw:
            try:
                listing_uuid = uuid.UUID(listing_id_raw)
            except ValueError:
                logger.warning("Stripe: checkout session had bad listing_id: %r", listing_id_raw)
                return {"received": True}
            listing = db.get(Listing, listing_uuid)
            if listing and listing.status == "active":
                listing.status = "reserved"
                db.commit()
                logger.info(
                    "Stripe: marked listing %s as reserved after checkout",
                    listing_uuid,
                )

    # Other event types we don't yet act on (refunds, disputes, etc.)
    # just return OK so Stripe doesn't retry.
    return {"received": True}
