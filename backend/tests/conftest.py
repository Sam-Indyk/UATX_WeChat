"""Shared fixtures for backend tests.

We talk to a real Postgres (the same one Docker brings up locally, and the
same one GitHub Actions starts as a service container in CI). Per the CLAUDE.md
"no SQLite" rule — dev/prod parity matters more than test speed.

Auth is bypassed in tests via FastAPI dependency_overrides. We construct
fake User rows directly and stub `require_user` to return one of them.
"""
from __future__ import annotations

import os
import uuid
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Force a test DB URL before app imports happen, so settings picks it up.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://uatx:uatx_dev@localhost:5432/uatx_wechat_test",
)
os.environ.setdefault("APP_ENV", "test")

from app.auth import require_user  # noqa: E402
from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.rate_limit import reset_for_tests as _reset_rate_limit  # noqa: E402


_engine = create_engine(os.environ["DATABASE_URL"], future=True)
_TestSession = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def _ensure_test_database() -> None:
    """Create the test database if it doesn't exist, then (re)create tables.

    Connects to the maintenance DB to issue CREATE DATABASE. Idempotent.

    We drop_all + create_all every session so schema changes (new columns,
    new constraints, etc.) take effect without manual cleanup between
    branches. Test data is wiped per-test by the `db` fixture anyway.
    """
    test_url = os.environ["DATABASE_URL"]
    # Strip the database name to get a maintenance URL pointing at `postgres`.
    db_name = test_url.rsplit("/", 1)[1]
    maintenance_url = test_url.rsplit("/", 1)[0] + "/postgres"
    maintenance = create_engine(maintenance_url, isolation_level="AUTOCOMMIT")
    with maintenance.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": db_name}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    maintenance.dispose()
    Base.metadata.drop_all(_engine)
    Base.metadata.create_all(_engine)


@pytest.fixture(scope="session", autouse=True)
def _init_db() -> None:
    _ensure_test_database()


@pytest.fixture()
def db() -> Iterator[Session]:
    """Per-test session that wipes table data before yielding.

    We TRUNCATE rather than drop+recreate to keep tests fast. Also
    resets the in-memory message rate-limit counter so one test's
    sends don't poison the next.
    """
    with _engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE feedback_submissions, messages, conversations, listings, enrollments, courses, users RESTART IDENTITY CASCADE"
            )
        )
    _reset_rate_limit()
    session = _TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def make_user(db: Session):
    def _make(
        user_id: str | None = None,
        email: str | None = None,
        display_name: str = "Test User",
    ) -> User:
        uid = user_id or f"user_{uuid.uuid4().hex[:16]}"
        u = User(
            id=uid,
            email=email or f"{uid}@student.uaustin.org",
            display_name=display_name,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        return u

    return _make


@pytest.fixture()
def client(db: Session, make_user) -> Iterator[TestClient]:
    """A TestClient where the auth dependency is overridden to return `current_user`.

    Tests can swap `current_user` by calling `client.set_user(...)` (we attach it).
    """
    current = make_user()

    def _override_get_db() -> Iterator[Session]:
        yield db

    def _override_require_user() -> User:
        return current

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[require_user] = _override_require_user

    with TestClient(app) as c:
        c.current_user = current  # type: ignore[attr-defined]

        def _set_user(user: User) -> None:
            nonlocal current
            current = user
            app.dependency_overrides[require_user] = lambda: current
            c.current_user = current  # type: ignore[attr-defined]

        c.set_user = _set_user  # type: ignore[attr-defined]
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def anon_client() -> Iterator[TestClient]:
    """A TestClient with NO auth override — used to test the 401 path.

    We DO override get_db so the request reaches the auth dependency without
    needing a real DB connection from the unauthenticated path.
    """
    def _override_get_db() -> Iterator[Session]:
        s = _TestSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
