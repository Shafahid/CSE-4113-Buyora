from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models import AuthSession, Base, User, UserProfile

ORIGIN = {"Origin": "http://localhost:3000"}


@pytest.fixture
def client(settings, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        execution_options={"schema_translate_map": {"buyora": None, "public": None}},
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr("app.main.create_db_engine", lambda _: engine)
    with TestClient(create_app(settings)) as client:
        yield client, engine


def test_registration_login_expiry_and_logout(client):
    client, engine = client
    data = {
        "email": "  Seller@Example.com ",
        "password": "correct horse",
        "display_name": " Seller ",
    }
    response = client.post("/auth/register", json=data, headers=ORIGIN)
    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "email": "seller@example.com",
        "display_name": "Seller",
    }
    with engine.connect() as conn:
        assert conn.execute(select(UserProfile.display_name)).scalar_one() == "Seller"
        assert conn.execute(select(User.password_hash)).scalar_one() != data["password"]
    assert client.post("/auth/register", json=data, headers=ORIGIN).status_code == 409
    bad = client.post(
        "/auth/login",
        json={"email": data["email"], "password": "wrong"},
        headers=ORIGIN,
    )
    unknown = client.post(
        "/auth/login",
        json={"email": "unknown@example.com", "password": "wrong"},
        headers=ORIGIN,
    )
    assert bad.status_code == unknown.status_code == 401
    assert bad.json() == unknown.json()
    assert client.get("/me").status_code == 401
    login = client.post("/auth/login", json=data, headers=ORIGIN)
    assert login.status_code == 200
    assert "httponly" in login.headers["set-cookie"].lower()
    token = client.cookies.get("buyora_session")
    assert client.get("/me").json() == response.json()
    with engine.begin() as conn:
        conn.execute(
            AuthSession.__table__.update().values(
                expires_at=datetime.now(UTC) - timedelta(seconds=1)
            )
        )
    assert client.get("/me").status_code == 401
    assert client.post("/auth/login", json=data, headers=ORIGIN).status_code == 200
    token = client.cookies.get("buyora_session")
    assert client.post("/auth/logout", headers=ORIGIN).status_code == 204
    assert client.post("/auth/logout", headers=ORIGIN).status_code == 204
    client.cookies.set("buyora_session", token)
    assert client.get("/me").status_code == 401


def test_csrf_origin_required(client):
    client, _ = client
    data = {
        "email": "seller@example.com",
        "password": "password123",
        "display_name": "Seller",
    }
    assert client.post("/auth/register", json=data).status_code == 403
    assert (
        client.post(
            "/auth/login", json=data, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/auth/logout", headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )


def test_local_swagger_origin_allowed_but_other_origins_rejected(client):
    client, _ = client
    data = {
        "email": "swagger@example.com",
        "password": "password123",
        "display_name": "Swagger",
    }
    with TestClient(client.app, base_url="http://127.0.0.1:8000") as local_client:
        assert (
            local_client.post(
                "/auth/register", json=data, headers={"Origin": "http://127.0.0.1:8000"}
            ).status_code
            == 201
        )
        assert (
            local_client.post(
                "/auth/logout", headers={"Origin": "http://localhost:8000"}
            ).status_code
            == 403
        )
