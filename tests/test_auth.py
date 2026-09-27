def test_signup_success(client):
    resp = client.post(
        "/auth/signup",
        json={"email": "a@example.com", "full_name": "Alice", "password": "password123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "a@example.com"
    assert "hashed_password" not in body


def test_signup_duplicate_email_rejected(client):
    payload = {"email": "dup@example.com", "full_name": "Bob", "password": "password123"}
    first = client.post("/auth/signup", json=payload)
    second = client.post("/auth/signup", json=payload)
    assert first.status_code == 201
    assert second.status_code == 409


def test_signup_invalid_email_rejected(client):
    resp = client.post(
        "/auth/signup",
        json={"email": "not-an-email", "full_name": "Bob", "password": "password123"},
    )
    assert resp.status_code == 422


def test_login_success_returns_jwt(client):
    client.post(
        "/auth/signup",
        json={"email": "c@example.com", "full_name": "Carol", "password": "password123"},
    )
    resp = client.post("/auth/login", json={"email": "c@example.com", "password": "password123"})
    assert resp.status_code == 200
    assert resp.json()["token_type"] == "bearer"
    assert len(resp.json()["access_token"]) > 10


def test_login_wrong_password_rejected(client):
    client.post(
        "/auth/signup",
        json={"email": "d@example.com", "full_name": "Dave", "password": "password123"},
    )
    resp = client.post("/auth/login", json={"email": "d@example.com", "password": "wrongpass"})
    assert resp.status_code == 401


def test_protected_endpoint_requires_token(client):
    resp = client.get("/bookings/")
    assert resp.status_code == 401


def test_protected_endpoint_rejects_garbage_token(client):
    resp = client.get("/bookings/", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401
