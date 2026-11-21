from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.pool import StaticPool

from app.main import create_app
from app.models import Base, Post, PostVersion, Product

ORIGIN = {"Origin": "http://localhost:3000"}
VERSION = {
    "headline": "First headline",
    "body": "First body",
    "offer": "10% off",
    "call_to_action": "Shop now",
    "hashtags": ["sale"],
    "platform": "Facebook",
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


def product(client):
    response = client.post(
        "/products",
        json={"name": "Item", "category": "Food", "price": "1.00"},
        headers=ORIGIN,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_post_versions_lifecycle_and_isolation(client):
    client, engine = client
    assert client.get("/products/1/posts").status_code == 401
    assert (
        client.post("/products/1/posts", json=VERSION, headers=ORIGIN).status_code
        == 401
    )
    login(client, "one@example.com")
    product_id = product(client)
    created = client.post(f"/products/{product_id}/posts", json=VERSION, headers=ORIGIN)
    assert created.status_code == 201
    post = created.json()
    post_id = post["id"]
    v1 = post["latest_version"]
    assert v1["version_number"] == 1 and v1["post_id"] == post_id
    assert v1["hashtags"] == ["sale"]
    other_post = client.post(
        f"/products/{product_id}/posts", json=VERSION, headers=ORIGIN
    ).json()
    revision = VERSION | {
        "headline": "Revised headline",
        "body": "Revised body",
        "hashtags": ["updated"],
    }
    v2_response = client.post(
        f"/posts/{post_id}/versions", json=revision, headers=ORIGIN
    )
    assert v2_response.status_code == 201
    v2 = v2_response.json()
    assert v2["version_number"] == 2
    assert client.get(f"/posts/{post_id}").json()["latest_version"] == v2
    assert [
        v["version_number"] for v in client.get(f"/posts/{post_id}/versions").json()
    ] == [2, 1]
    assert client.get(f"/posts/{post_id}/versions/{v1['id']}").json() == v1
    assert (
        client.get(f"/posts/{other_post['id']}/versions/{v2['id']}").status_code == 404
    )
    listing = client.get(f"/products/{product_id}/posts").json()
    assert len(listing) == 2
    listed = next(item for item in listing if item["id"] == post_id)
    assert listed["latest_version_id"] == v2["id"]
    assert listed["version_number"] == 2
    assert listed["headline"] == "Revised headline" and listed["platform"] == "Facebook"
    login(client, "two@example.com")
    assert client.get(f"/products/{product_id}/posts").status_code == 404
    assert (
        client.post(
            f"/products/{product_id}/posts", json=VERSION, headers=ORIGIN
        ).status_code
        == 404
    )
    assert client.get(f"/posts/{post_id}").status_code == 404
    assert client.get(f"/posts/{post_id}/versions").status_code == 404
    assert client.get(f"/posts/{post_id}/versions/{v1['id']}").status_code == 404
    assert (
        client.post(
            f"/posts/{post_id}/versions", json=VERSION, headers=ORIGIN
        ).status_code
        == 404
    )
    with engine.begin() as conn:
        conn.execute(
            Product.__table__.update()
            .where(Product.id == product_id)
            .values(deleted_at=datetime.now(UTC))
        )
    # Switch back to the owner to verify soft-deleted products are inaccessible.
    assert (
        client.post(
            "/auth/login",
            json={"email": "one@example.com", "password": "password123"},
            headers=ORIGIN,
        ).status_code
        == 200
    )
    assert client.get(f"/products/{product_id}/posts").status_code == 404
    assert client.get(f"/posts/{post_id}").status_code == 404
    assert client.get(f"/posts/{post_id}/versions").status_code == 404
    assert client.get(f"/posts/{post_id}/versions/{v1['id']}").status_code == 404
    assert (
        client.post(
            f"/posts/{post_id}/versions", json=VERSION, headers=ORIGIN
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/products/{product_id}/posts", json=VERSION, headers=ORIGIN
        ).status_code
        == 404
    )


@pytest.mark.parametrize("field", ["headline", "body", "platform"])
def test_blank_fields_rejected(client, field):
    client, _ = client
    login(client, "one@example.com")
    product_id = product(client)
    assert (
        client.post(
            f"/products/{product_id}/posts",
            json=VERSION | {field: "  "},
            headers=ORIGIN,
        ).status_code
        == 422
    )


def test_csrf_for_creation_and_revision(client):
    client, _ = client
    login(client, "one@example.com")
    product_id = product(client)
    assert (
        client.post(
            f"/products/{product_id}/posts",
            json=VERSION,
            headers={"Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    post_id = client.post(
        f"/products/{product_id}/posts", json=VERSION, headers=ORIGIN
    ).json()["id"]
    assert (
        client.post(
            f"/posts/{post_id}/versions",
            json=VERSION,
            headers={"Origin": "https://evil.example"},
        ).status_code
        == 403
    )


def test_first_post_and_version_are_atomic(client):
    client, engine = client
    login(client, "one@example.com")
    product_id = product(client)

    def fail(*args):
        raise RuntimeError("test insert failure")

    event.listen(PostVersion, "before_insert", fail)
    try:
        with pytest.raises(RuntimeError):
            client.post(f"/products/{product_id}/posts", json=VERSION, headers=ORIGIN)
    finally:
        event.remove(PostVersion, "before_insert", fail)
    with engine.connect() as conn:
        assert conn.execute(select(Post.id)).first() is None


def test_postgresql_lock_targets_parent_post():
    query = (
        select(Post)
        .join(Product, Post.product_id == Product.id)
        .with_for_update(of=Post)
    )
    assert "FOR UPDATE OF posts" in str(query.compile(dialect=postgresql.dialect()))
