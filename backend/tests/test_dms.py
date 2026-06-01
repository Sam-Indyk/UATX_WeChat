"""Tests for direct messages — listing-less conversations between two users.

Exercised from the Classmates page via `POST /api/users/{other_id}/dm`.
"""
import uuid

import pytest
from sqlalchemy.orm import Session

from app.models import Course, Listing


def test_start_dm_creates_conversation(client, make_user) -> None:
    other = make_user(display_name="Eitan")
    r = client.post(f"/api/users/{other.id}/dm")
    assert r.status_code == 201
    body = r.json()
    assert body["listing"] is None
    # Backend canonicalizes the pair into buyer_id/other_user_id, so we
    # just check that both parties appear somewhere on the conversation.
    parties = {body["buyer"]["id"], body["other_user"]["id"]}
    assert parties == {client.current_user.id, other.id}


def test_start_dm_is_idempotent(client, make_user) -> None:
    other = make_user()
    a = client.post(f"/api/users/{other.id}/dm").json()
    b = client.post(f"/api/users/{other.id}/dm").json()
    assert a["id"] == b["id"]


def test_dm_canonicalization_works_both_directions(client, make_user) -> None:
    """A→B and B→A must return the same conversation row."""
    other = make_user()
    a = client.post(f"/api/users/{other.id}/dm").json()
    # Swap to other user and call A→B (where "A" is now `other`, "B" is the
    # original current_user). Should get the same conversation back.
    client.set_user(other)
    b = client.post(f"/api/users/{a['buyer']['id'] if a['buyer']['id'] != other.id else a['other_user']['id']}/dm").json()
    assert a["id"] == b["id"]


def test_cant_dm_yourself(client) -> None:
    r = client.post(f"/api/users/{client.current_user.id}/dm")
    assert r.status_code == 400


def test_dm_unknown_user(client) -> None:
    r = client.post("/api/users/user_doesnotexist/dm")
    assert r.status_code == 404


def test_dm_requires_auth(anon_client) -> None:
    r = anon_client.post("/api/users/user_x/dm")
    assert r.status_code == 401


def test_dm_appears_in_inbox(client, make_user) -> None:
    other = make_user(display_name="Eitan")
    dm_id = client.post(f"/api/users/{other.id}/dm").json()["id"]
    # Send a message so the conversation has activity.
    client.post(f"/api/conversations/{dm_id}/messages", json={"body": "hey"})

    rows = client.get("/api/conversations").json()
    assert len(rows) == 1
    assert rows[0]["id"] == dm_id
    assert rows[0]["listing"] is None


def test_inbox_mixes_listing_and_dm_conversations(client, make_user, db: Session) -> None:
    other = make_user(display_name="Eitan")
    # Listing convo: current_user becomes a buyer of `other`'s listing.
    course = Course(id=uuid.uuid4(), code="PHIL 101", title="Intro to Philosophy")
    db.add(course)
    db.flush()
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
    listing_convo = client.post(f"/api/listings/{listing.id}/contact").json()
    dm_convo = client.post(f"/api/users/{other.id}/dm").json()

    rows = client.get("/api/conversations").json()
    ids = {r["id"] for r in rows}
    assert listing_convo["id"] in ids
    assert dm_convo["id"] in ids
    # The listing convo has a listing; the DM does not.
    by_id = {r["id"]: r for r in rows}
    assert by_id[listing_convo["id"]]["listing"] is not None
    assert by_id[dm_convo["id"]]["listing"] is None
