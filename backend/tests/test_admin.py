"""Tests for the admin-only feedback dashboard endpoint."""
import pytest

from app.config import settings


@pytest.fixture()
def as_admin(client, monkeypatch):
    """Mark the current client user as an admin by injecting their
    email into the ADMIN_EMAILS allowlist for the duration of the test."""
    monkeypatch.setattr(settings, "ADMIN_EMAILS", client.current_user.email)
    return client


def test_list_feedback_admin_sees_all(client, monkeypatch, make_user) -> None:
    # Capture admin BEFORE swapping — otherwise current_user changes
    # and we lose the reference we want to swap back to.
    admin_user = client.current_user
    monkeypatch.setattr(settings, "ADMIN_EMAILS", admin_user.email)

    # Two users each submit feedback.
    client.post("/api/feedback", json={"category": "feature", "body": "Add rides"})
    other = make_user(email="other@student.uaustin.org", display_name="Other")
    client.set_user(other)
    client.post("/api/feedback", json={"category": "bug", "body": "Found a bug"})

    # Swap back to the admin user.
    client.set_user(admin_user)

    r = client.get("/api/admin/feedback")
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 2
    # Newest first.
    assert rows[0]["body"] == "Found a bug"
    assert rows[1]["body"] == "Add rides"
    # Joined submitter info comes through.
    assert rows[0]["user_email"] == "other@student.uaustin.org"
    assert rows[0]["user_display_name"] == "Other"


def test_list_feedback_non_admin_403(client) -> None:
    """Default test user has a random @student.uaustin.org email that
    is NOT in the ADMIN_EMAILS list — should be rejected."""
    r = client.get("/api/admin/feedback")
    assert r.status_code == 403


def test_list_feedback_anon_401(anon_client) -> None:
    r = anon_client.get("/api/admin/feedback")
    assert r.status_code == 401


def test_me_returns_is_admin_true_for_admin(as_admin) -> None:
    r = as_admin.get("/api/me")
    assert r.status_code == 200
    assert r.json()["is_admin"] is True


def test_me_returns_is_admin_false_for_non_admin(client) -> None:
    r = client.get("/api/me")
    assert r.status_code == 200
    assert r.json()["is_admin"] is False
