from tests.conftest import signup_and_login, create_centre_with_test


def _make_booking(client, headers, test):
    return client.post(
        "/bookings/",
        json={"test_id": test["id"], "appointment_time": "2026-10-01T10:00:00"},
        headers=headers,
    ).json()


def test_payment_success_confirms_booking(client):
    headers = signup_and_login(client)
    _, test = create_centre_with_test(client, headers)
    booking = _make_booking(client, headers, test)

    resp = client.post(
        "/payments/",
        json={"booking_id": booking["id"], "force_status": "SUCCESS"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "SUCCESS"

    booking_after = client.get(f"/bookings/{booking['id']}", headers=headers).json()
    assert booking_after["status"] == "CONFIRMED"


def test_payment_failure_marks_booking_failed(client):
    headers = signup_and_login(client)
    _, test = create_centre_with_test(client, headers)
    booking = _make_booking(client, headers, test)

    resp = client.post(
        "/payments/",
        json={"booking_id": booking["id"], "force_status": "FAILED"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "FAILED"

    booking_after = client.get(f"/bookings/{booking['id']}", headers=headers).json()
    assert booking_after["status"] == "FAILED"


def test_cannot_pay_for_already_confirmed_booking(client):
    headers = signup_and_login(client)
    _, test = create_centre_with_test(client, headers)
    booking = _make_booking(client, headers, test)

    client.post(
        "/payments/", json={"booking_id": booking["id"], "force_status": "SUCCESS"}, headers=headers
    )
    second = client.post(
        "/payments/", json={"booking_id": booking["id"], "force_status": "SUCCESS"}, headers=headers
    )
    assert second.status_code == 400


def test_cannot_pay_for_others_booking(client):
    headers_a = signup_and_login(client, email="pa@example.com")
    headers_b = signup_and_login(client, email="pb@example.com")
    _, test = create_centre_with_test(client, headers_a)
    booking = _make_booking(client, headers_a, test)

    resp = client.post(
        "/payments/", json={"booking_id": booking["id"], "force_status": "SUCCESS"}, headers=headers_b
    )
    assert resp.status_code == 403


def test_pay_for_invalid_booking_id(client):
    headers = signup_and_login(client)
    resp = client.post(
        "/payments/", json={"booking_id": "does-not-exist", "force_status": "SUCCESS"}, headers=headers
    )
    assert resp.status_code == 404
