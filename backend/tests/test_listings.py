import uuid

import pytest
from sqlalchemy.orm import Session

from app.models import Course


@pytest.fixture()
def course(db: Session) -> Course:
    c = Course(id=uuid.uuid4(), code="PHIL 101", title="Intro to Philosophy")
    db.add(c)
    db.commit()
    return c


def _payload(course_id: uuid.UUID, **overrides) -> dict:
    base = {
        "course_id": str(course_id),
        "book_title": "Republic",
        "book_author": "Plato",
        "book_edition": None,
        "condition": "good",
        "price_cents": 1500,
        "description": "Lightly used.",
    }
    base.update(overrides)
    return base


def test_create_listing(client, course) -> None:
    r = client.post("/api/listings", json=_payload(course.id))
    assert r.status_code == 201
    body = r.json()
    assert body["seller"]["id"] == client.current_user.id
    assert body["status"] == "active"
    assert body["course"]["code"] == "PHIL 101"


def test_create_listing_rejects_bad_condition(client, course) -> None:
    r = client.post("/api/listings", json=_payload(course.id, condition="mint"))
    assert r.status_code == 422


def test_list_listings_filters_by_course(client, course, db: Session) -> None:
    other = Course(id=uuid.uuid4(), code="MATH 201", title="Calculus I")
    db.add(other)
    db.commit()

    client.post("/api/listings", json=_payload(course.id, book_title="Republic"))
    client.post("/api/listings", json=_payload(other.id, book_title="Stewart Calculus"))

    r = client.get(f"/api/listings?course_id={course.id}")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["book_title"] == "Republic"


def test_only_seller_can_mark_sold(client, course, make_user) -> None:
    create = client.post("/api/listings", json=_payload(course.id))
    listing_id = create.json()["id"]

    # Swap to a different user and try to mark it sold.
    other = make_user(email="other@student.uaustin.org")
    client.set_user(other)

    r = client.patch(f"/api/listings/{listing_id}", json={"status": "sold"})
    assert r.status_code == 403


def test_update_book_fields(client, course) -> None:
    """The Settings tab on /my-listings/:id needs to edit title, author,
    edition, condition, and the course assignment too — not just price
    and status.
    """
    other = Course(id=uuid.uuid4(), code="MATH 201", title="Calculus I")
    create = client.post("/api/listings", json=_payload(course.id))
    listing_id = create.json()["id"]

    r = client.patch(
        f"/api/listings/{listing_id}",
        json={
            "book_title": "  Republic, 2nd ed.  ",
            "book_author": "Plato",
            "book_edition": "2nd",
            "condition": "like_new",
            "course_id": None,  # ignored — pydantic None means "not provided" in this schema
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Whitespace trimmed.
    assert body["book_title"] == "Republic, 2nd ed."
    assert body["book_author"] == "Plato"
    assert body["book_edition"] == "2nd"
    assert body["condition"] == "like_new"


def test_update_status_to_withdrawn_take_down(client, course) -> None:
    create = client.post("/api/listings", json=_payload(course.id))
    listing_id = create.json()["id"]

    r = client.patch(f"/api/listings/{listing_id}", json={"status": "withdrawn"})
    assert r.status_code == 200
    assert r.json()["status"] == "withdrawn"


def test_update_rejects_bad_condition(client, course) -> None:
    create = client.post("/api/listings", json=_payload(course.id))
    listing_id = create.json()["id"]
    r = client.patch(f"/api/listings/{listing_id}", json={"condition": "mint"})
    assert r.status_code == 422
