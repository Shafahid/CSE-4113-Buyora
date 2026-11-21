from datetime import UTC, datetime
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, event, select
from sqlalchemy.pool import StaticPool

from app.api.routes.products import get_storage
from app.core.storage import StorageError
from app.main import create_app
from app.models import Base, ProductImage

ORIGIN = {"Origin": "http://localhost:3000"}


class MockStorage:
    def __init__(self):
        self.objects = {}
        self.removed = []
        self.fail = False

    def upload(self, key, data, content_type):
        if self.fail:
            raise StorageError()
        self.objects[key] = (data, content_type)

    def remove(self, key):
        self.removed.append(key)
        self.objects.pop(key, None)

    def signed_url(self, key):
        return "https://storage.example/signed/" + key


@pytest.fixture
def setup(settings, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        execution_options={"schema_translate_map": {"public": None, "buyora": None}},
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr("app.main.create_db_engine", lambda _: engine)
    storage = MockStorage()
    app = create_app(settings)
    app.dependency_overrides[get_storage] = lambda: storage
    monkeypatch.setattr("app.api.routes.products.get_storage", lambda _: storage)
    with TestClient(app) as client:
        yield client, engine, storage


def login(client, email):
    user = {"email": email, "password": "password123", "display_name": "Seller"}
    assert client.post("/auth/register", json=user, headers=ORIGIN).status_code == 201
    assert client.post("/auth/login", json=user, headers=ORIGIN).status_code == 200


def make_product(client):
    return client.post(
        "/products",
        json={"name": "Item", "category": "Food", "price": "1.00"},
        headers=ORIGIN,
    ).json()["id"]


def image_bytes(fmt="PNG"):
    out = BytesIO()
    Image.new("RGB", (2, 2)).save(out, format=fmt)
    return out.getvalue()


@pytest.mark.parametrize(
    "fmt,mime", [("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp")]
)
def test_upload_and_owner_detail(setup, fmt, mime):
    client, engine, storage = setup
    login(client, "one@example.com")
    product_id = make_product(client)
    response = client.post(
        f"/products/{product_id}/images",
        files={"file": ("misleading.txt", image_bytes(fmt), "text/plain")},
        headers=ORIGIN,
    )
    assert response.status_code == 201
    assert "storage_key" not in response.json()
    assert len(storage.objects) == 1
    key, (_, detected) = next(iter(storage.objects.items()))
    assert detected == mime
    with engine.connect() as conn:
        assert conn.execute(select(ProductImage.storage_key)).scalar_one() == key
    detail = client.get(f"/products/{product_id}")
    assert detail.status_code == 200
    assert detail.json()["images"][0]["url"].endswith(key)
    assert detail.headers["cache-control"] == "private, no-store"
    login(client, "two@example.com")
    assert client.get(f"/products/{product_id}").status_code == 404
    assert (
        client.post(
            f"/products/{product_id}/images",
            files={"file": ("a.png", image_bytes(), "image/png")},
            headers=ORIGIN,
        ).status_code
        == 404
    )


def test_invalid_and_oversize_files(setup):
    client, engine, storage = setup
    login(client, "one@example.com")
    product_id = make_product(client)
    url = f"/products/{product_id}/images"
    assert (
        client.post(
            url, files={"file": ("a.png", b"not an image", "image/png")}, headers=ORIGIN
        ).status_code
        == 422
    )
    assert (
        client.post(
            url,
            files={"file": ("a.png", b"x" * (5 * 1024 * 1024 + 1), "image/png")},
            headers=ORIGIN,
        ).status_code
        == 413
    )
    assert storage.objects == {}
    with engine.connect() as conn:
        assert conn.execute(select(ProductImage)).first() is None


def test_failed_upload_does_not_insert(setup):
    client, engine, storage = setup
    login(client, "one@example.com")
    product_id = make_product(client)
    storage.fail = True
    response = client.post(
        f"/products/{product_id}/images",
        files={"file": ("a.png", image_bytes(), "image/png")},
        headers=ORIGIN,
    )
    assert response.status_code == 502
    with engine.connect() as conn:
        assert conn.execute(select(ProductImage)).first() is None


def test_database_failure_cleans_up_upload(setup):
    client, engine, storage = setup
    login(client, "one@example.com")
    product_id = make_product(client)

    def fail_insert(*args):
        raise RuntimeError("simulated database failure")

    event.listen(ProductImage, "before_insert", fail_insert)
    try:
        with pytest.raises(RuntimeError):
            client.post(
                f"/products/{product_id}/images",
                files={"file": ("a.png", image_bytes(), "image/png")},
                headers=ORIGIN,
            )
    finally:
        event.remove(ProductImage, "before_insert", fail_insert)
    assert len(storage.removed) == 1
    assert storage.objects == {}
    with engine.connect() as conn:
        assert conn.execute(select(ProductImage)).first() is None


def test_missing_session_csrf_and_deleted_product(setup):
    from app.models import Product

    client, engine, storage = setup
    path = "/products/1/images"
    image = {"file": ("a.png", image_bytes(), "image/png")}
    assert client.post(path, files=image, headers=ORIGIN).status_code == 401
    assert client.get("/products/1").status_code == 401
    login(client, "one@example.com")
    product_id = make_product(client)
    path = f"/products/{product_id}/images"
    assert (
        client.post(
            path, files=image, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    with engine.begin() as conn:
        conn.execute(
            Product.__table__.update()
            .where(Product.id == product_id)
            .values(deleted_at=datetime.now(UTC))
        )
    assert client.post(path, files=image, headers=ORIGIN).status_code == 404
    assert client.get(f"/products/{product_id}").status_code == 404
    assert storage.objects == {}


def test_remove_image_and_preserve_images_on_soft_delete(setup):
    client, engine, storage = setup
    login(client, "one@example.com")
    product_id = make_product(client)
    image = client.post(
        f"/products/{product_id}/images",
        files={"file": ("a.png", image_bytes(), "image/png")},
        headers=ORIGIN,
    ).json()
    image_id = image["id"]
    other_product = make_product(client)
    assert (
        client.delete(
            f"/products/{other_product}/images/{image_id}", headers=ORIGIN
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/products/{product_id}/images/{image_id}", headers=ORIGIN
        ).status_code
        == 204
    )
    assert len(storage.removed) == 1
    with engine.connect() as conn:
        assert (
            conn.execute(
                select(ProductImage).where(ProductImage.id == image_id)
            ).first()
            is None
        )
    assert (
        client.delete(
            f"/products/{product_id}/images/{image_id}", headers=ORIGIN
        ).status_code
        == 404
    )
    image2 = client.post(
        f"/products/{product_id}/images",
        files={"file": ("a.png", image_bytes(), "image/png")},
        headers=ORIGIN,
    ).json()
    assert client.delete(f"/products/{product_id}", headers=ORIGIN).status_code == 204
    with engine.connect() as conn:
        assert (
            conn.execute(
                select(ProductImage).where(ProductImage.id == image2["id"])
            ).first()
            is not None
        )
    assert len(storage.objects) == 1


def test_remove_failure_keeps_image_row_and_cross_seller_denied(setup, monkeypatch):
    client, engine, storage = setup
    login(client, "one@example.com")
    product_id = make_product(client)
    image = client.post(
        f"/products/{product_id}/images",
        files={"file": ("a.png", image_bytes(), "image/png")},
        headers=ORIGIN,
    ).json()
    path = f"/products/{product_id}/images/{image['id']}"
    old_cookie = client.cookies.get("buyora_session")
    login(client, "two@example.com")
    assert client.delete(path, headers=ORIGIN).status_code == 404
    client.cookies.set(
        "buyora_session", old_cookie, domain="testserver.local", path="/"
    )

    def fail(key):
        raise StorageError()

    monkeypatch.setattr(storage, "remove", fail)
    assert client.delete(path, headers=ORIGIN).status_code == 502
    with engine.connect() as conn:
        assert (
            conn.execute(
                select(ProductImage).where(ProductImage.id == image["id"])
            ).first()
            is not None
        )


def test_duplicate_copies_details_without_copying_images(setup):
    client, engine, storage = setup
    login(client, "one@example.com")
    product_id = make_product(client)
    image = client.post(
        f"/products/{product_id}/images",
        files={"file": ("a.png", image_bytes(), "image/png")},
        headers=ORIGIN,
    ).json()
    duplicate = client.post(f"/products/{product_id}/duplicate", headers=ORIGIN)
    assert duplicate.status_code == 201
    copy_id = duplicate.json()["id"]
    assert client.get(f"/products/{copy_id}").json()["images"] == []
    assert len(client.get(f"/products/{product_id}").json()["images"]) == 1
    with engine.connect() as conn:
        assert (
            conn.execute(
                select(ProductImage.product_id).where(ProductImage.id == image["id"])
            ).scalar_one()
            == product_id
        )
    assert len(storage.objects) == 1
