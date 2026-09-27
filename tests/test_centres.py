from tests.conftest import signup_and_login, create_centre_with_test


def test_create_centre_with_tests(client):
    headers = signup_and_login(client)
    centre, test = create_centre_with_test(client, headers)
    assert centre["name"] == "City Diagnostics"
    assert len(centre["tests"]) == 1
    assert test["price"] == 500.0


def test_create_centre_requires_auth(client):
    resp = client.post("/centres/", json={"name": "X", "location": "Y"})
    assert resp.status_code == 401


def test_list_centres_pagination(client):
    headers = signup_and_login(client)
    for i in range(3):
        client.post(
            "/centres/", json={"name": f"Centre {i}", "location": "Mumbai"}, headers=headers
        )

    resp = client.get("/centres/?limit=2&offset=0")
    body = resp.json()
    assert resp.status_code == 200
    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_list_centres_filter_by_location(client):
    headers = signup_and_login(client)
    client.post("/centres/", json={"name": "A", "location": "Delhi"}, headers=headers)
    client.post("/centres/", json={"name": "B", "location": "Chennai"}, headers=headers)

    resp = client.get("/centres/?location=delhi")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["location"] == "Delhi"


def test_get_centre_not_found(client):
    resp = client.get("/centres/does-not-exist")
    assert resp.status_code == 404


def test_duplicate_test_name_in_same_centre_rejected(client):
    headers = signup_and_login(client)
    centre, _ = create_centre_with_test(client, headers)
    resp = client.post(
        f"/centres/{centre['id']}/tests",
        json={"name": "Complete Blood Count", "price": 600.0},
        headers=headers,
    )
    assert resp.status_code == 400


def test_add_test_to_missing_centre_returns_404(client):
    headers = signup_and_login(client)
    resp = client.post(
        "/centres/does-not-exist/tests", json={"name": "X-Ray", "price": 100}, headers=headers
    )
    assert resp.status_code == 404
