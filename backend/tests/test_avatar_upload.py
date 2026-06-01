"""Tests for POST /api/me/avatar — profile picture upload.

Mirrors the listing-image upload test pattern: monkeypatch the storage
uploader so we don't hit Supabase from CI.
"""
import pytest

from app.routers import me as me_router


@pytest.fixture(autouse=True)
def fake_uploader(monkeypatch):
    def _fake(*, user_id, content_type: str, data: bytes) -> str:
        return f"https://fake-storage/avatars/{user_id}/avatar.{content_type.split('/')[-1]}"

    monkeypatch.setattr(me_router, "upload_avatar", _fake)
    yield _fake


def _png_bytes() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


def test_avatar_upload_happy_path(client) -> None:
    r = client.post(
        "/api/me/avatar",
        files={"file": ("me.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["avatar_url"].startswith("https://fake-storage/avatars/")
    assert body["avatar_url"].endswith(".png")

    # Subsequent GET /api/me reflects the URL.
    g = client.get("/api/me").json()
    assert g["avatar_url"] == body["avatar_url"]


def test_avatar_upload_rejects_non_image(client) -> None:
    r = client.post(
        "/api/me/avatar",
        files={"file": ("doc.pdf", b"%PDF-1.5" + b"\x00" * 50, "application/pdf")},
    )
    assert r.status_code == 415


def test_avatar_upload_rejects_oversized(client) -> None:
    big = b"\x89PNG\r\n\x1a\n" + b"\x00" * (5 * 1024 * 1024 + 1)
    r = client.post(
        "/api/me/avatar",
        files={"file": ("big.png", big, "image/png")},
    )
    assert r.status_code == 413


def test_avatar_upload_requires_auth(anon_client) -> None:
    r = anon_client.post(
        "/api/me/avatar",
        files={"file": ("me.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 401
