"""Tests for the user-feedback submission endpoint."""
from sqlalchemy import select

from app.models import FeedbackSubmission


def test_submit_feedback_happy_path(client, db) -> None:
    r = client.post(
        "/api/feedback",
        json={"category": "feature", "body": "Add a study-group chat per class."},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["category"] == "feature"
    assert body["body"] == "Add a study-group chat per class."
    # Row landed in the DB attributed to the authed user.
    row = db.execute(select(FeedbackSubmission)).scalar_one()
    assert row.user_id == client.current_user.id


def test_submit_feedback_rejects_unknown_category(client) -> None:
    r = client.post(
        "/api/feedback", json={"category": "nonsense", "body": "hi"}
    )
    assert r.status_code == 422


def test_submit_feedback_rejects_empty_body(client) -> None:
    r = client.post("/api/feedback", json={"category": "bug", "body": ""})
    assert r.status_code == 422


def test_submit_feedback_requires_auth(anon_client) -> None:
    r = anon_client.post(
        "/api/feedback", json={"category": "feature", "body": "anything"}
    )
    assert r.status_code == 401
