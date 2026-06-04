"""Clerk JWT verification.

The frontend passes Clerk's session JWT as `Authorization: Bearer <token>`.
We verify it against Clerk's JWKS (cached in-process), optionally enforce
an email-domain allowlist (off by default — see ALLOWED_EMAIL_DOMAINS in
config.py), and upsert the user into our `users` table on first sight.

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

    # Pull what the JWT gave us. Clerk's DEFAULT session token doesn't
    # include email/name/picture — you'd have to configure a JWT template
    # in the Clerk dashboard to add them. We code defensively for the
    # default case.
    raw_email = (
        claims.get("email")
        or claims.get("email_address")
        or claims.get("primary_email_address")
    )
    raw_name = claims.get("name") or claims.get("full_name")
    raw_avatar = claims.get("picture") or claims.get("image_url")

    # Synthesize fallbacks for the INSERT case. Clerk's default session token
    # doesn't include email/name/picture (you'd have to configure a JWT
    # template). Without these fallbacks, the first INSERT would put empty
    # string in users.email and collide with the UNIQUE constraint on the
    # second user. The .local TLD is reserved (RFC 6762).
    email = raw_email or f"{user_id}@clerk.local"
    display_name = (
        raw_name
        or (raw_email.split("@")[0] if raw_email else f"User {user_id[-6:]}")
    )

    if raw_email:
        _enforce_email_domain(raw_email)

    user = db.get(User, user_id)
    if user is None:
        user = User(
            id=user_id,
            email=email,
            display_name=display_name,
            avatar_url=raw_avatar,
        )
        db.add(user)
        db.flush()
    else:
        # Refresh metadata ONLY when Clerk actually provided the claim.
        # If we used the synthesized fallback (raw_* is falsy), we'd
        # overwrite anything the user edited via the Settings page —
        # which is the bug Sam hit where his display_name kept resetting
        # to "User q2Nia7" after he saved a real name.
        if raw_email and user.email != raw_email:
            user.email = raw_email
        if raw_name and user.display_name != raw_name:
            user.display_name = raw_name
        if raw_avatar and user.avatar_url != raw_avatar:
            user.avatar_url = raw_avatar

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
