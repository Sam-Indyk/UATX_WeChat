"""Backend foundation for the Inbox-replacement UX (PR #17, runway).

Three endpoints introduced together:
  - GET /api/me/unread-counts       — per-context breakdown for the new nav
  - GET /api/me/listings            — listings I posted, with per-listing unread
  - GET /api/listings/{id}/conversations — seller-only view of all buyers on a listing
"""
import uuid

import pytest
from sqlalchemy.orm import Session

from app.models import Conversation, Course, Listing, Message


@pytest.fixture()
def course(db: Session) -> Course:
    c = Course(id=uuid.uuid4(), code="PHIL 101", title="Intro to Philosophy")
    db.add(c)
    db.commit()
    return c


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/me/unread-counts
# ─────────────────────────────────────────────────────────────────────────────


def test_unread_counts_empty_for_new_user(client) -> None:
    r = client.get("/api/me/unread-counts")
    assert r.status_code == 200
    assert r.json() == {"listings": 0, "inquiries": 0, "dms": 0, "total": 0}


def test_unread_counts_breaks_down_by_context(client, make_user, course, db: Session) -> None:
    me = client.current_user
    other = make_user(email="other@student.uaustin.org")

    # 1. I'm the SELLER on a listing convo → counts as "listings"
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
    db.flush()
    # Other contacts me about my listing
    client.set_user(other)
    seller_convo_id = client.post(f"/api/listings/{my_listing.id}/contact").json()["id"]
    client.post(
        f"/api/conversations/{seller_convo_id}/messages", json={"body": "hi seller"}
    )

    # 2. I'm the BUYER on a different listing → counts as "inquiries"
    their_listing = Listing(
        id=uuid.uuid4(),
        seller_id=other.id,
        course_id=course.id,
        book_title="Meno",
        book_author="Plato",
        condition="good",
        price_cents=1200,
        description="",
    )
    db.add(their_listing)
    db.commit()
    client.set_user(me)
    buyer_convo_id = client.post(f"/api/listings/{their_listing.id}/contact").json()["id"]
    # `me` sent this one — won't count as "my" unread.
    # Now `other` replies.
    client.set_user(other)
    client.post(
        f"/api/conversations/{buyer_convo_id}/messages", json={"body": "yes available"}
    )

    # 3. DM from `other` to me → counts as "dms"
    client.post(f"/api/users/{me.id}/dm")
    dm_convo_id = client.post(f"/api/users/{me.id}/dm").json()["id"]
    client.post(
        f"/api/conversations/{dm_convo_id}/messages", json={"body": "hey want to study?"}
    )

    # Switch back to me; check counts
    client.set_user(me)
    r = client.get("/api/me/unread-counts").json()
    assert r["listings"] == 1, r
    assert r["inquiries"] == 1, r
    assert r["dms"] == 1, r
    assert r["total"] == 3, r


def test_unread_counts_excludes_own_outgoing(client, make_user, course, db: Session) -> None:
    me = client.current_user
    other = make_user(email="other@student.uaustin.org")
    listing = Listing(
        id=uuid.uuid4(),
        seller_id=other.id,
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
    # I send a message — that's outgoing, doesn't count for me.
    client.post(f"/api/conversations/{convo_id}/messages", json={"body": "hi"})

    r = client.get("/api/me/unread-counts").json()
    assert r == {"listings": 0, "inquiries": 0, "dms": 0, "total": 0}


def test_unread_counts_requires_auth(anon_client) -> None:
    r = anon_client.get("/api/me/unread-counts")
    assert r.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/me/listings
# ─────────────────────────────────────────────────────────────────────────────


def test_my_listings_returns_only_mine(client, make_user, course, db: Session) -> None:
    me = client.current_user
    other = make_user(email="other@student.uaustin.org")

    mine = Listing(
        id=uuid.uuid4(),
        seller_id=me.id,
        course_id=course.id,
        book_title="Republic",
        book_author="Plato",
        condition="good",
        price_cents=1500,
        description="",
    )
    theirs = Listing(
        id=uuid.uuid4(),
        seller_id=other.id,
        course_id=course.id,
        book_title="Meno",
        book_author="Plato",
        condition="good",
        price_cents=1200,
        description="",
    )
    db.add_all([mine, theirs])
    db.commit()

    rows = client.get("/api/me/listings").json()
    ids = {r["id"] for r in rows}
    assert str(mine.id) in ids
    assert str(theirs.id) not in ids


def test_my_listings_includes_unread_per_listing(
    client, make_user, course, db: Session
) -> None:
    me = client.current_user
    other = make_user(email="buyer@student.uaustin.org")

    listing = Listing(
        id=uuid.uuid4(),
        seller_id=me.id,
        course_id=course.id,
        book_title="Republic",
        book_author="Plato",
        condition="good",
        price_cents=1500,
        description="",
    )
    db.add(listing)
    db.commit()

    # Buyer sends two messages.
    client.set_user(other)
    convo_id = client.post(f"/api/listings/{listing.id}/contact").json()["id"]
    client.post(f"/api/conversations/{convo_id}/messages", json={"body": "1"})
    client.post(f"/api/conversations/{convo_id}/messages", json={"body": "2"})

    # Back to seller — listing shows unread_count=2.
    client.set_user(me)
    rows = client.get("/api/me/listings").json()
    assert len(rows) == 1
    assert rows[0]["unread_count"] == 2


def test_my_listings_requires_auth(anon_client) -> None:
    r = anon_client.get("/api/me/listings")
    assert r.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/listings/{id}/conversations
# ─────────────────────────────────────────────────────────────────────────────


def test_listing_conversations_seller_sees_all_buyers(
    client, make_user, course, db: Session
) -> None:
    me = client.current_user
    buyer_a = make_user(email="a@student.uaustin.org", display_name="A")
    buyer_b = make_user(email="b@student.uaustin.org", display_name="B")

    listing = Listing(
        id=uuid.uuid4(),
        seller_id=me.id,
        course_id=course.id,
        book_title="Republic",
        book_author="Plato",
        condition="good",
        price_cents=1500,
        description="",
    )
    db.add(listing)
    db.commit()

    # Two different buyers each open a thread.
    client.set_user(buyer_a)
    client.post(f"/api/listings/{listing.id}/contact")
    client.set_user(buyer_b)
    client.post(f"/api/listings/{listing.id}/contact")

    client.set_user(me)
    rows = client.get(f"/api/listings/{listing.id}/conversations").json()
    assert len(rows) == 2
    buyers = {r["buyer"]["id"] for r in rows}
    assert buyers == {buyer_a.id, buyer_b.id}


def test_listing_conversations_buyer_gets_403(client, make_user, course, db: Session) -> None:
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
    # I'm a buyer here. Shouldn't be able to see ALL buyers on the seller's listing.
    client.post(f"/api/listings/{listing.id}/contact")

    r = client.get(f"/api/listings/{listing.id}/conversations")
    assert r.status_code == 403


def test_listing_conversations_unknown_listing_404(client) -> None:
    r = client.get(f"/api/listings/{uuid.uuid4()}/conversations")
    assert r.status_code == 404


def test_listing_conversations_includes_per_thread_unread(
    client, make_user, course, db: Session
) -> None:
    me = client.current_user
    buyer = make_user(email="buyer@student.uaustin.org")
    listing = Listing(
        id=uuid.uuid4(),
        seller_id=me.id,
        course_id=course.id,
        book_title="Republic",
        book_author="Plato",
        condition="good",
        price_cents=1500,
        description="",
    )
    db.add(listing)
    db.commit()

    client.set_user(buyer)
    convo_id = client.post(f"/api/listings/{listing.id}/contact").json()["id"]
    client.post(f"/api/conversations/{convo_id}/messages", json={"body": "ping"})

    client.set_user(me)
    rows = client.get(f"/api/listings/{listing.id}/conversations").json()
    assert rows[0]["unread_count"] == 1


def test_listing_conversations_requires_auth(anon_client) -> None:
    r = anon_client.get(f"/api/listings/{uuid.uuid4()}/conversations")
    assert r.status_code == 401
