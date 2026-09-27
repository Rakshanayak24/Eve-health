import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.config import settings

# Each test gets a brand new in-memory SQLite database, so tests never leak
# state into each other and no external Postgres is required to run the
# suite.
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture()
def db_engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def webhook_secret():
    return settings.webhook_shared_secret


def signup_and_login(client, email="patient@example.com", password="supersecret1"):
    client.post(
        "/auth/signup",
        json={"email": email, "full_name": "Test Patient", "password": password},
    )
    resp = client.post("/auth/login", json={"email": email, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_centre_with_test(client, headers, price=500.0):
    resp = client.post(
        "/centres/",
        json={
            "name": "City Diagnostics",
            "location": "Bengaluru",
            "tests": [{"name": "Complete Blood Count", "price": price}],
        },
        headers=headers,
    )
    centre = resp.json()
    return centre, centre["tests"][0]
