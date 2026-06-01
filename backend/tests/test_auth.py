from app.auth import _upsert_user


def test_me_requires_auth(anon_client) -> None:
    r = anon_client.get("/api/me")
    assert r.status_code == 401


def test_me_returns_current_user(client) -> None:
    r = client.get("/api/me")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == client.current_user.id
    assert body["email"].endswith("@student.uaustin.org")


def test_upsert_synthesizes_unique_email_when_jwt_omits_it(db) -> None:
    """Default Clerk session JWTs don't include email. Two users signing in
    with empty-email claims must not collide on the users.email UNIQUE
    constraint — we synthesize <sub>@clerk.local for each.
    """
    a = _upsert_user(db, {"sub": "user_alpha"})
    db.flush()
    b = _upsert_user(db, {"sub": "user_beta"})
    db.commit()

    assert a.email == "user_alpha@clerk.local"
    assert b.email == "user_beta@clerk.local"
    assert a.email != b.email
    assert a.display_name.startswith("User ")
    assert b.display_name.startswith("User ")


def test_upsert_prefers_real_email_when_present(db) -> None:
    user = _upsert_user(
        db,
        {"sub": "user_gamma", "email": "gamma@student.uaustin.org", "name": "Gamma G."},
    )
    db.commit()
    assert user.email == "gamma@student.uaustin.org"
    assert user.display_name == "Gamma G."


def test_upsert_idempotent_for_returning_user(db) -> None:
    claims = {"sub": "user_delta", "email": "delta@student.uaustin.org", "name": "Delta"}
    a = _upsert_user(db, claims)
    db.commit()
    b = _upsert_user(db, claims)
    db.commit()
    assert a.id == b.id
    assert a.email == b.email
