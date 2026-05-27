"""Clerk JWT verification.

The frontend passes Clerk's session JWT as `Authorization: Bearer <token>`.
We verify it against Clerk's JWKS (cached in-process), enforce the
@student.uaustin.org email-domain restriction, and upsert the user into
our `users` table on first sight.

In tests, `require_user` is overridden via FastAPI's dependency_overrides so
we don't have to talk to Clerk's JWKS endpoint.
"""
from __future__ import annotations

import time
from functools import lru_cache
from typing import Any

import httpx
from fastapi import Depends, Header, HTTPException, status
from jose import jwt
from jose.exceptions import JWTError
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import User


_JWKS_CACHE: dict[str, Any] = {"keys": None, "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 60 * 60  # 1 hour


def _fetch_jwks() -> dict[str, Any]:
    now = time.time()
    if _JWKS_CACHE["keys"] is not None and now - _JWKS_CACHE["fetched_at"] < _JWKS_TTL_SECONDS:
        return _JWKS_CACHE["keys"]

    if not settings.CLERK_JWKS_URL:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CLERK_JWKS_URL not configured",
        )

    resp = httpx.get(settings.CLERK_JWKS_URL, timeout=10.0)
    resp.raise_for_status()
    _JWKS_CACHE["keys"] = resp.json()
    _JWKS_CACHE["fetched_at"] = now
    return _JWKS_CACHE["keys"]


def _verify_clerk_jwt(token: str) -> dict[str, Any]:
    try:
        jwks = _fetch_jwks()
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        key = next((k for k in jwks["keys"] if k["kid"] == kid), None)
        if key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown signing key"
            )

        options = {"verify_aud": bool(settings.CLERK_AUDIENCE)}
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.CLERK_AUDIENCE or None,
            issuer=settings.CLERK_ISSUER or None,
            options=options,
        )
        return claims
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}"
        ) from e


def _enforce_email_domain(email: str) -> None:
    # Empty allowlist = open to all domains. We let in non-UATX emails so
    # incoming students without an official @student.uaustin.org address
    # can still buy books from upperclassmen.
    allowed = settings.allowed_domains_list
    if not allowed:
        return
    if "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Email missing domain"
        )
    domain = email.rsplit("@", 1)[1].lower()
    if domain not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Email domain {domain!r} not allowed",
        )


def _upsert_user(db: Session, claims: dict[str, Any]) -> User:
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing sub")

    # Clerk session JWTs commonly include these claims. If your Clerk JWT template
    # uses different keys, adjust here.
    email = (
        claims.get("email")
        or claims.get("email_address")
        or claims.get("primary_email_address")
        or ""
    )
    display_name = (
        claims.get("name")
        or claims.get("full_name")
        or (email.split("@")[0] if email else "user")
    )
    avatar_url = claims.get("picture") or claims.get("image_url")

    if email:
        _enforce_email_domain(email)

    user = db.get(User, user_id)
    if user is None:
        user = User(
            id=user_id,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
        )
        db.add(user)
        db.flush()
    else:
        # Refresh metadata if Clerk's copy is newer.
        if email and user.email != email:
            user.email = email
        if display_name and user.display_name != display_name:
            user.display_name = display_name
        if avatar_url and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url

    return user


def require_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: verifies the Clerk JWT and returns the DB User row.

    Overridden in tests via app.dependency_overrides.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token"
        )

    token = authorization.split(" ", 1)[1].strip()
    claims = _verify_clerk_jwt(token)
    user = _upsert_user(db, claims)
    db.commit()
    db.refresh(user)
    return user
