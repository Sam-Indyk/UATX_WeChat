"""Listing-image upload via Supabase Storage.

Backend-proxied (FastAPI -> Supabase) rather than signed-URL-direct
because the auth + size + MIME validation lives server-side anyway and
listing images are small. The Supabase bucket is configured public-read
so the URL we store in listings.image_url is directly fetchable.

Tests can swap out the implementation via the `upload_listing_image`
dependency override on FastAPI's `app.dependency_overrides`.
"""
from __future__ import annotations

import uuid
from typing import Protocol

import httpx
from fastapi import HTTPException, status

from app.config import settings


MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _extension_for(content_type: str) -> str:
    return {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }[content_type]


class ListingImageUploader(Protocol):
    def __call__(self, *, listing_id: uuid.UUID, content_type: str, data: bytes) -> str: ...


def upload_listing_image(*, listing_id: uuid.UUID, content_type: str, data: bytes) -> str:
    """Push the bytes to Supabase Storage and return the public URL.

    Caller is responsible for validating content_type and size BEFORE
    handing the bytes here — this function will still defend itself, but
    the 4xx response surface lives in the router.
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported content type: {content_type}")
    if len(data) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB)")
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image uploads are not configured on this server",
        )

    ext = _extension_for(content_type)
    # Random path inside listings/<id>/ so re-uploads don't collide and
    # so a leaked URL doesn't let an attacker overwrite an existing image.
    object_path = f"listings/{listing_id}/{uuid.uuid4().hex}.{ext}"
    upload_url = (
        f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/"
        f"{settings.SUPABASE_STORAGE_BUCKET}/{object_path}"
    )

    resp = httpx.post(
        upload_url,
        headers={
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
            "Content-Type": content_type,
            "x-upsert": "true",
        },
        content=data,
        timeout=30.0,
    )
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Storage upload failed: {resp.status_code} {resp.text[:200]}",
        )

    # Public bucket → directly fetchable URL.
    return (
        f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/public/"
        f"{settings.SUPABASE_STORAGE_BUCKET}/{object_path}"
    )


def upload_avatar(*, user_id: str, content_type: str, data: bytes) -> str:
    """Upload a profile picture for `user_id` and return the public URL.

    Stored under `avatars/<user_id>/<random>.<ext>` in the same Supabase
    bucket we use for listing images — keeps configuration minimal (one
    bucket, two prefixes).
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported content type: {content_type}")
    if len(data) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB)")
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image uploads are not configured on this server",
        )

    ext = _extension_for(content_type)
    object_path = f"avatars/{user_id}/{uuid.uuid4().hex}.{ext}"
    upload_url = (
        f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/"
        f"{settings.SUPABASE_STORAGE_BUCKET}/{object_path}"
    )

    resp = httpx.post(
        upload_url,
        headers={
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
            "Content-Type": content_type,
            "x-upsert": "true",
        },
        content=data,
        timeout=30.0,
    )
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Storage upload failed: {resp.status_code} {resp.text[:200]}",
        )

    return (
        f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/public/"
        f"{settings.SUPABASE_STORAGE_BUCKET}/{object_path}"
    )
