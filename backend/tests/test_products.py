from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models import Base, Product

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


def login_as(client, email):
    assert (
        client.post(
            "/auth/register",
            json={"email": email, "password": "password123", "display_name": "Seller"},
            headers=ORIGIN,
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/auth/login",
            json={"email": email, "password": "password123"},
            headers=ORIGIN,
        ).status_code
        == 200
    )


def test_creation_listing_and_seller_isolation(client):
    client, engine = client
    product = {
        "name": "  Camera  ",
        "category": " Devices ",
        "price": "123.45",
        "description": "A camera",
        "features": ["lens"],
        "warranty": "One year",
        "delivery_info": "Home",
        "return_policy": "Seven days",
    }
    assert client.get("/products").status_code == 401
    assert client.post("/products", json=product, headers=ORIGIN).status_code == 401
    login_as(client, "one@example.com")
    first = client.post("/products", json=product, headers=ORIGIN)
    assert first.status_code == 201
    data = first.json()
    assert data["name"] == "Camera"
    assert data["category"] == "Devices"
    assert data["price"] == "123.45"
    assert data["features"] == ["lens"]
    assert data["delivery_info"] == "Home"
    assert data["currency"] == "BDT"
    assert client.get("/products").json() == [data]
    login_as(client, "two@example.com")
    assert client.get("/products").json() == []
    second = client.post(
        "/products",
        json={"name": "Book", "category": "Books", "price": 0},
        headers=ORIGIN,
    )
    assert second.status_code == 201
    assert second.json()["seller_id"] != data["seller_id"]
    with engine.begin() as conn:
        conn.execute(
            Product.__table__.update()
            .where(Product.id == second.json()["id"])
            .values(status="archived")
        )
    assert client.get("/products").json() == []
    with engine.begin() as conn:
        conn.execute(
            Product.__table__.update()
            .where(Product.id == second.json()["id"])
            .values(status="active", deleted_at=datetime.now(UTC))
        )
    assert client.get("/products").json() == []


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "   "},
        {"category": ""},
        {"price": "-1"},
        {"price": "NaN"},
        {"price": "1.234"},
        {"price": "10000000000"},
        {"seller_id": 5},
    ],
)
def test_invalid_products(client, changes):
    client, _ = client
    login_as(client, "seller@example.com")
    data = {"name": "Book", "category": "Books", "price": "9.50"} | changes
    assert client.post("/products", json=data, headers=ORIGIN).status_code == 422
    assert client.get("/products").json() == []


def test_product_creation_requires_trusted_origin(client):
    client, _ = client
    login_as(client, "seller@example.com")
    data = {"name": "Book", "category": "Books", "price": "9.50"}
    assert (
        client.post(
            "/products", json=data, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )


def test_openapi_examples_are_valid_products(client):
    from app.api.routes.products import ProductCreate, ProductResponse

    client, _ = client
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    ProductCreate.model_validate(schemas["ProductCreate"]["examples"][0])
    ProductResponse.model_validate(schemas["ProductResponse"]["examples"][0])


def test_create_response_documentation_example(client):
    from app.api.routes.products import ProductResponse

    client, _ = client
    schema = client.get("/openapi.json").json()
    example = schema["paths"]["/products"]["post"]["responses"]["201"]["content"][
        "application/json"
    ]["example"]
    assert ProductResponse.model_validate(example).price == 1250


def test_product_lifecycle_and_seller_isolation(client):
    client, engine = client
    login_as(client, "one@example.com")
    original = client.post(
        "/products",
        json={
            "name": "Original",
            "category": "Books",
            "price": "15.50",
            "description": "Old description",
            "features": ["one"],
            "warranty": "Year",
            "delivery_info": "Courier",
            "return_policy": "Week",
        },
        headers=ORIGIN,
    ).json()
    product_id = original["id"]
    path = f"/products/{product_id}"
    for patch in (
        {"name": "   "},
        {"category": None},
        {"price": "-1"},
        {"price": None},
        {"features": None},
        {"status": None},
        {"status": "deleted"},
        {"seller_id": 999},
        {"updated_at": "2020-01-01T00:00:00Z"},
    ):
        assert client.patch(path, json=patch, headers=ORIGIN).status_code == 422
    edited = client.patch(
        path,
        json={"name": " Updated ", "price": "20.25", "description": None},
        headers=ORIGIN,
    )
    assert edited.status_code == 200
    assert edited.json()["name"] == "Updated"
    assert edited.json()["description"] is None
    assert edited.json()["category"] == "Books"
    assert edited.json()["features"] == ["one"]
    assert (
        client.patch(path, json={"status": "archived"}, headers=ORIGIN).json()["status"]
        == "archived"
    )
    assert client.get("/products").json() == []
    assert [x["id"] for x in client.get("/products?status=archived").json()] == [
        product_id
    ]
    assert client.get("/products?status=invalid").status_code == 422
    duplicate = client.post(path + "/duplicate", headers=ORIGIN)
    assert duplicate.status_code == 201
    copy = duplicate.json()
    assert copy["id"] != product_id
    assert copy["seller_id"] == original["seller_id"]
    assert copy["status"] == "active"
    for key in (
        "name",
        "category",
        "price",
        "description",
        "features",
        "warranty",
        "delivery_info",
        "return_policy",
        "currency",
    ):
        assert copy[key] == edited.json()[key]
    assert client.get(f"/products/{copy['id']}").json()["images"] == []
    assert (
        client.patch(path, json={"status": "active"}, headers=ORIGIN).json()["status"]
        == "active"
    )
    assert client.get("/products?status=archived").json() == []
    assert client.delete(path, headers=ORIGIN).status_code == 204
    assert client.get(path).status_code == 404
    assert client.patch(path, json={"name": "x"}, headers=ORIGIN).status_code == 404
    assert client.post(path + "/duplicate", headers=ORIGIN).status_code == 404
    assert client.delete(path, headers=ORIGIN).status_code == 404
    with engine.connect() as conn:
        product = conn.execute(
            Product.__table__.select().where(Product.id == product_id)
        ).first()
        assert product is not None and product.deleted_at is not None
    login_as(client, "two@example.com")
    other = f"/products/{copy['id']}"
    assert client.get(other).status_code == 404
    assert (
        client.patch(other, json={"name": "stolen"}, headers=ORIGIN).status_code == 404
    )
    assert client.post(other + "/duplicate", headers=ORIGIN).status_code == 404
    assert client.delete(other, headers=ORIGIN).status_code == 404


def test_new_product_mutations_require_auth_and_origin(client):
    client, _ = client
    for method, path in (
        ("patch", "/products/1"),
        ("post", "/products/1/duplicate"),
        ("delete", "/products/1"),
        ("delete", "/products/1/images/1"),
    ):
        kwargs = {"json": {"name": "x"}} if method == "patch" else {}
        assert (
            getattr(client, method)(path, headers=ORIGIN, **kwargs).status_code == 401
        )
    login_as(client, "one@example.com")
    product_id = client.post(
        "/products",
        json={"name": "Item", "category": "Food", "price": 1},
        headers=ORIGIN,
    ).json()["id"]
    for method, path in (
        ("patch", f"/products/{product_id}"),
        ("post", f"/products/{product_id}/duplicate"),
        ("delete", f"/products/{product_id}"),
        ("delete", f"/products/{product_id}/images/1"),
    ):
        kwargs = {"json": {"name": "x"}} if method == "patch" else {}
        assert (
            getattr(client, method)(
                path, headers={"Origin": "https://evil.example"}, **kwargs
            ).status_code
            == 403
        )
