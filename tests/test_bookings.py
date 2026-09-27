from tests.conftest import signup_and_login, create_centre_with_test


def test_create_booking_success(client):
    headers = signup_and_login(client)
    _, test = create_centre_with_test(client, headers)

    resp = client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": "2026-10-01T10:00:00"},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "PENDING"
    assert body["amount"] == 500.0


def test_create_booking_invalid_test_id(client):
    headers = signup_and_login(client)
    resp = client.post(
        "/bookings/",
        json={"test_id": "not-a-real-test", "appointment_time": "2026-10-01T10:00:00"},
        headers=headers,
    )
    assert resp.status_code == 404


def test_user_cannot_view_others_booking(client):
    headers_a = signup_and_login(client, email="a@example.com")
    headers_b = signup_and_login(client, email="b@example.com")
    _, test = create_centre_with_test(client, headers_a)

    booking = client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": "2026-10-01T10:00:00"},
        headers=headers_a,
    ).json()

    resp = client.get(f"/bookings/{booking['id']}", headers=headers_b)
    assert resp.status_code == 403


def test_list_bookings_only_returns_own(client):
    headers_a = signup_and_login(client, email="a2@example.com")
    headers_b = signup_and_login(client, email="b2@example.com")
    _, test = create_centre_with_test(client, headers_a)

    client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": "2026-10-01T10:00:00"},
        headers=headers_a,
    )

    resp = client.get("/bookings/", headers=headers_b)
    assert resp.json()["total"] == 0


def test_cancel_pending_booking(client):
    headers = signup_and_login(client)
    _, test = create_centre_with_test(client, headers)
    booking = client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": "2026-10-01T10:00:00"},
        headers=headers,
    ).json()

    resp = client.patch(f"/bookings/{booking['id']}/cancel", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"


def test_cancel_confirmed_booking_rejected(client):
    headers = signup_and_login(client)
    _, test = create_centre_with_test(client, headers)
    booking = client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": "2026-10-01T10:00:00"},
        headers=headers,
    ).json()

    client.post(
        "/payments/",
        json={"booking_id": booking["id"], "force_status": "SUCCESS"},
        headers=headers,
    )

    resp = client.patch(f"/bookings/{booking['id']}/cancel", headers=headers)
    assert resp.status_code == 400


def test_cancelling_twice_is_idempotent(client):
    headers = signup_and_login(client)
    _, test = create_centre_with_test(client, headers)
    booking = client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": "2026-10-01T10:00:00"},
        headers=headers,
    ).json()

    first = client.patch(f"/bookings/{booking['id']}/cancel", headers=headers)
    second = client.patch(f"/bookings/{booking['id']}/cancel", headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "CANCELLED"
