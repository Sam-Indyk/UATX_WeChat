def test_update_display_name(client) -> None:
    r = client.patch("/api/me", json={"display_name": "Sam Indyk"})
    assert r.status_code == 200
    assert r.json()["display_name"] == "Sam Indyk"

    # Subsequent GET reflects the change.
    g = client.get("/api/me")
    assert g.json()["display_name"] == "Sam Indyk"


def test_update_display_name_trims_whitespace(client) -> None:
    r = client.patch("/api/me", json={"display_name": "   Sam Indyk   "})
    assert r.status_code == 200
    assert r.json()["display_name"] == "Sam Indyk"


def test_update_rejects_blank_display_name(client) -> None:
    # Pydantic min_length=1 catches an empty string before our handler.
    r = client.patch("/api/me", json={"display_name": ""})
    assert r.status_code == 422


def test_update_rejects_whitespace_only_display_name(client) -> None:
    # Whitespace passes Pydantic's length check; our handler enforces non-blank.
    r = client.patch("/api/me", json={"display_name": "   "})
    assert r.status_code == 422


def test_update_requires_auth(anon_client) -> None:
    r = anon_client.patch("/api/me", json={"display_name": "Hacker"})
    assert r.status_code == 401


def test_update_ignores_unknown_fields(client) -> None:
    # The schema doesn't accept email; it should be silently ignored, not 422.
    r = client.patch(
        "/api/me",
        json={"display_name": "Sam", "email": "spoof@evil.com"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["display_name"] == "Sam"
    # Email is not changed by this endpoint.
    assert body["email"] != "spoof@evil.com"
