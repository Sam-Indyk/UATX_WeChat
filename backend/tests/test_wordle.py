"""Tests for the Wordle completion-tracking endpoints."""


def test_complete_records_win(client) -> None:
    r = client.post(
        "/api/wordle/complete",
        json={"game_index": 0, "num_guesses": 4},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["game_index"] == 0
    assert body["num_guesses"] == 4


def test_complete_is_idempotent_and_keeps_best(client) -> None:
    """Replaying a game already won doesn't insert a duplicate row.
    The recorded num_guesses only goes DOWN (improves), never up."""
    a = client.post(
        "/api/wordle/complete", json={"game_index": 5, "num_guesses": 5}
    ).json()
    # Worse attempt — should be ignored.
    b = client.post(
        "/api/wordle/complete", json={"game_index": 5, "num_guesses": 6}
    ).json()
    assert a["id"] == b["id"]
    assert b["num_guesses"] == 5
    # Better attempt — should update.
    c = client.post(
        "/api/wordle/complete", json={"game_index": 5, "num_guesses": 3}
    ).json()
    assert c["id"] == a["id"]
    assert c["num_guesses"] == 3


def test_list_me_returns_only_my_wins(client, make_user) -> None:
    client.post("/api/wordle/complete", json={"game_index": 0, "num_guesses": 4})
    client.post("/api/wordle/complete", json={"game_index": 2, "num_guesses": 6})

    # Switch user — their wins should not appear in the other user's list.
    other = make_user(email="other@student.uaustin.org")
    client.set_user(other)
    client.post("/api/wordle/complete", json={"game_index": 1, "num_guesses": 5})

    r = client.get("/api/wordle/me")
    assert r.status_code == 200
    rows = r.json()
    assert [row["game_index"] for row in rows] == [1]


def test_complete_rejects_negative_game_index(client) -> None:
    r = client.post(
        "/api/wordle/complete", json={"game_index": -1, "num_guesses": 4}
    )
    assert r.status_code == 422


def test_complete_rejects_zero_guesses(client) -> None:
    r = client.post(
        "/api/wordle/complete", json={"game_index": 0, "num_guesses": 0}
    )
    assert r.status_code == 422


def test_endpoints_require_auth(anon_client) -> None:
    r = anon_client.get("/api/wordle/me")
    assert r.status_code == 401
    r = anon_client.post(
        "/api/wordle/complete", json={"game_index": 0, "num_guesses": 4}
    )
    assert r.status_code == 401
