from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models import Base, Product, Simulation

ORIGIN = {"Origin": "http://localhost:3000"}
NADIA = {
    "name": "Nadia",
    "characteristics": {
        "label": "Budget student",
        "age_range": {"min": 18, "max": 24},
        "occupation": "Student",
    },
    "needs": ["Practical everyday essentials at a student-friendly price"],
    "preferences": [],
    "budget_sensitivity": "high",
}


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


def draft(client):
    product_id = client.post(
        "/products",
        json={"name": "Item", "category": "Food", "price": "1.00"},
        headers=ORIGIN,
    ).json()["id"]
    version_id = client.post(
        f"/products/{product_id}/posts",
        json={"headline": "First", "body": "Body", "platform": "Facebook"},
        headers=ORIGIN,
    ).json()["latest_version"]["id"]
    simulation_id = client.post(
        "/simulations", json={"post_version_id": version_id}, headers=ORIGIN
    ).json()["id"]
    return product_id, simulation_id


def test_persona_lifecycle_and_characteristic_merge(client):
    client, _ = client
    login(client, "one@example.com")
    _, simulation_id = draft(client)
    path = f"/simulations/{simulation_id}/personas"
    assert client.get(path).json() == []
    response = client.post(path, json=NADIA, headers=ORIGIN)
    assert response.status_code == 201
    nadia = response.json()
    assert nadia["is_selected"] is True
    assert nadia["budget_sensitivity"] == "high"
    assert nadia["simulation_id"] == simulation_id
    assert client.get(path).json() == [nadia]
    persona_path = f"{path}/{nadia['id']}"
    edited = client.patch(
        persona_path,
        json={"characteristics": {"label": "Careful shopper"}},
        headers=ORIGIN,
    )
    assert edited.status_code == 200
    assert edited.json()["characteristics"] == {
        "label": "Careful shopper",
        "age_range": {"min": 18, "max": 24},
        "occupation": "Student",
    }
    assert (
        client.patch(persona_path, json={"is_selected": False}, headers=ORIGIN).json()[
            "is_selected"
        ]
        is False
    )
    assert (
        client.patch(
            persona_path, json={"budget_sensitivity": None}, headers=ORIGIN
        ).json()["budget_sensitivity"]
        is None
    )
    for name in ("Rafi", "Farhana", "Arif"):
        created = client.post(path, json={"name": name}, headers=ORIGIN)
        assert created.status_code == 201
        assert created.json()["needs"] == []
        assert created.json()["preferences"] == []
        assert created.json()["budget_sensitivity"] is None
    assert len(client.get(path).json()) == 4
    assert client.delete(persona_path, headers=ORIGIN).status_code == 204
    assert len(client.get(path).json()) == 3
    assert client.delete(persona_path, headers=ORIGIN).status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"name": "  "},
        {"name": None},
        {"characteristics": {"age_range": {"min": 30, "max": 20}}},
        {"characteristics": {"age_range": {"min": "18"}}},
        {"needs": "not a list"},
        {"preferences": None},
        {"is_selected": None},
        {"budget_sensitivity": "extreme"},
        {"simulation_id": 55},
        {"id": 100},
        {"created_at": "2020-01-01T00:00:00Z"},
    ],
)
def test_invalid_patch(client, body):
    client, _ = client
    login(client, "one@example.com")
    _, simulation_id = draft(client)
    path = f"/simulations/{simulation_id}/personas"
    persona_id = client.post(path, json=NADIA, headers=ORIGIN).json()["id"]
    assert (
        client.patch(f"{path}/{persona_id}", json=body, headers=ORIGIN).status_code
        == 422
    )


def test_ownership_simulation_scope_and_started_status(client):
    client, engine = client
    assert client.get("/simulations/1/personas").status_code == 401
    assert (
        client.post("/simulations/1/personas", json=NADIA, headers=ORIGIN).status_code
        == 401
    )
    assert (
        client.patch(
            "/simulations/1/personas/1", json={"is_selected": False}, headers=ORIGIN
        ).status_code
        == 401
    )
    assert client.delete("/simulations/1/personas/1", headers=ORIGIN).status_code == 401
    login(client, "one@example.com")
    product_id, simulation_id = draft(client)
    _, other_id = draft(client)
    path = f"/simulations/{simulation_id}/personas"
    persona_id = client.post(path, json=NADIA, headers=ORIGIN).json()["id"]
    other_path = f"/simulations/{other_id}/personas/{persona_id}"
    assert (
        client.patch(
            other_path, json={"is_selected": False}, headers=ORIGIN
        ).status_code
        == 404
    )
    assert client.delete(other_path, headers=ORIGIN).status_code == 404
    assert (
        client.post(
            path, json=NADIA, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"{path}/{persona_id}",
            json={"is_selected": False},
            headers={"Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"{path}/{persona_id}", headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    login(client, "two@example.com")
    assert client.get(path).status_code == 404
    assert client.post(path, json=NADIA, headers=ORIGIN).status_code == 404
    assert (
        client.patch(
            f"{path}/{persona_id}", json={"is_selected": False}, headers=ORIGIN
        ).status_code
        == 404
    )
    assert client.delete(f"{path}/{persona_id}", headers=ORIGIN).status_code == 404
    assert (
        client.post(
            "/auth/login",
            json={"email": "one@example.com", "password": "password123"},
            headers=ORIGIN,
        ).status_code
        == 200
    )
    with engine.begin() as conn:
        conn.execute(
            Simulation.__table__.update()
            .where(Simulation.id == simulation_id)
            .values(status="running")
        )
    assert client.get(path).status_code == 200
    assert (
        client.patch(
            f"{path}/999999", json={"is_selected": False}, headers=ORIGIN
        ).status_code
        == 404
    )
    assert client.delete(f"{path}/999999", headers=ORIGIN).status_code == 404
    assert client.post(path, json=NADIA, headers=ORIGIN).status_code == 409
    assert (
        client.patch(
            f"{path}/{persona_id}", json={"is_selected": False}, headers=ORIGIN
        ).status_code
        == 409
    )
    assert client.delete(f"{path}/{persona_id}", headers=ORIGIN).status_code == 409
    with engine.begin() as conn:
        conn.execute(
            Product.__table__.update()
            .where(Product.id == product_id)
            .values(deleted_at=datetime.now(UTC))
        )
    assert client.get(path).status_code == 404
