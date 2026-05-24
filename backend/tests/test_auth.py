def test_me_requires_auth(anon_client) -> None:
    r = anon_client.get("/api/me")
    assert r.status_code == 401


def test_me_returns_current_user(client) -> None:
    r = client.get("/api/me")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == client.current_user.id
    assert body["email"].endswith("@student.uaustin.org")
