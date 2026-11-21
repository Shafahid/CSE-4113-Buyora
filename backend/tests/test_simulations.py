from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models import Base, Product, Simulation

ORIGIN = {"Origin": "http://localhost:3000"}


@pytest.fixture
def client(settings, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        execution_options={"schema_translate_map": {"public": None, "buyora": None}},
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr("app.main.create_db_engine", lambda _: engine)
    with TestClient(create_app(settings)) as client:
        yield client, engine


def login(client, email):
    user = {"email": email, "password": "password123", "display_name": "Seller"}
    assert client.post("/auth/register", json=user, headers=ORIGIN).status_code == 201
    assert client.post("/auth/login", json=user, headers=ORIGIN).status_code == 200


def post_version(client):
    product_id = client.post(
        "/products",
        json={"name": "Item", "category": "Food", "price": "1.00"},
        headers=ORIGIN,
    ).json()["id"]
    post = client.post(
        f"/products/{product_id}/posts",
        json={"headline": "First", "body": "Body", "platform": "Facebook"},
        headers=ORIGIN,
    ).json()
    return product_id, post["id"], post["latest_version"]["id"]


def test_draft_setup_reload_clear_and_frozen_version(client):
    client, _ = client
    login(client, "one@example.com")
    product_id, post_id, version_id = post_version(client)
    result = client.post(
        "/simulations", json={"post_version_id": version_id}, headers=ORIGIN
    )
    assert result.status_code == 201
    draft = result.json()
    assert draft["post_version_id"] == version_id
    assert draft["status"] == "draft" and draft["language"] == "en"
    assert draft["audience_settings"] == {}
    simulation_id = draft["id"]
    settings = {
        "location": "Dhaka",
        "age_range": {"min": 18, "max": 34},
        "interests": ["food", "fashion"],
        "purchasing_preference": "cash_on_delivery",
        "budget_sensitivity": "medium",
        "product_needs": "Delivery",
    }
    response = client.patch(
        f"/simulations/{simulation_id}",
        json={"audience_settings": settings, "language": "bn"},
        headers=ORIGIN,
    )
    assert response.status_code == 200
    assert response.json()["audience_settings"] == settings
    assert client.get(f"/simulations/{simulation_id}").json() == response.json()
    new_version = client.post(
        f"/posts/{post_id}/versions",
        json={"headline": "Second", "body": "New", "platform": "Facebook"},
        headers=ORIGIN,
    )
    assert new_version.status_code == 201
    assert new_version.json()["id"] != version_id
    assert (
        client.get(f"/simulations/{simulation_id}").json()["post_version_id"]
        == version_id
    )
    response = client.patch(
        f"/simulations/{simulation_id}",
        json={"audience_settings": {"age_range": {"min": 55}}},
        headers=ORIGIN,
    )
    assert response.json()["audience_settings"] == {"age_range": {"min": 55}}
    assert response.json()["language"] == "bn"
    response = client.patch(
        f"/simulations/{simulation_id}", json={"audience_settings": {}}, headers=ORIGIN
    )
    assert response.json()["audience_settings"] == {}
    assert client.get(f"/simulations/{simulation_id}").json()["audience_settings"] == {}
    assert product_id > 0


@pytest.mark.parametrize(
    "body",
    [
        {"audience_settings": {"age_range": {"min": 35, "max": 18}}},
        {"audience_settings": {"age_range": {"min": "18"}}},
        {"audience_settings": {"age_range": {"max": 34}}},
        {"audience_settings": {"age_range": {"min": 55, "max": None}}},
        {"audience_settings": {"purchasing_preference": "cash"}},
        {"audience_settings": {"budget_sensitivity": "very high"}},
        {"audience_settings": {"interests": "food"}},
        {"audience_settings": {"unknown": 1}},
        {"audience_settings": None},
        {"language": "fr"},
        {"post_version_id": 123},
        {"status": "completed"},
        {"product_snapshot": {}},
    ],
)
def test_invalid_updates_are_rejected(client, body):
    client, _ = client
    login(client, "one@example.com")
    _, _, version_id = post_version(client)
    simulation_id = client.post(
        "/simulations", json={"post_version_id": version_id}, headers=ORIGIN
    ).json()["id"]
    assert (
        client.patch(
            f"/simulations/{simulation_id}", json=body, headers=ORIGIN
        ).status_code
        == 422
    )


def test_ownership_status_deleted_and_csrf(client):
    client, engine = client
    assert client.get("/simulations/1").status_code == 401
    assert (
        client.post(
            "/simulations", json={"post_version_id": 1}, headers=ORIGIN
        ).status_code
        == 401
    )
    assert client.patch("/simulations/1", json={}, headers=ORIGIN).status_code == 401
    login(client, "one@example.com")
    product_id, _, version_id = post_version(client)
    assert (
        client.post(
            "/simulations",
            json={"post_version_id": version_id},
            headers={"Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    simulation_id = client.post(
        "/simulations",
        json={
            "post_version_id": version_id,
            "audience_settings": {"age_range": {"min": 55}},
        },
        headers=ORIGIN,
    ).json()["id"]
    path = f"/simulations/{simulation_id}"
    assert (
        client.patch(
            path, json={}, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    login(client, "two@example.com")
    assert (
        client.post(
            "/simulations", json={"post_version_id": version_id}, headers=ORIGIN
        ).status_code
        == 404
    )
    assert client.get(path).status_code == 404
    assert client.patch(path, json={}, headers=ORIGIN).status_code == 404
    with engine.begin() as conn:
        conn.execute(
            Simulation.__table__.update()
            .where(Simulation.id == simulation_id)
            .values(status="queued")
        )
    assert (
        client.post(
            "/auth/login",
            json={"email": "one@example.com", "password": "password123"},
            headers=ORIGIN,
        ).status_code
        == 200
    )
    assert (
        client.patch(path, json={"language": "bn"}, headers=ORIGIN).status_code == 409
    )
    assert client.get(path).json()["status"] == "queued"
    with engine.begin() as conn:
        conn.execute(
            Product.__table__.update()
            .where(Product.id == product_id)
            .values(deleted_at=datetime.now(UTC))
        )
    assert client.get(path).status_code == 404
    assert client.patch(path, json={}, headers=ORIGIN).status_code == 404
    assert (
        client.post(
            "/simulations", json={"post_version_id": version_id}, headers=ORIGIN
        ).status_code
        == 404
    )
