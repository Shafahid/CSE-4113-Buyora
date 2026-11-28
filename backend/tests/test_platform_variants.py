from datetime import UTC, datetime

import pytest
from processing_fakes import FakeProcessingAdmission
from pydantic import ValidationError
from sqlalchemy import select
from test_posts import ORIGIN, VERSION, login, product
from test_posts import client as post_client

from app.models.platform_variant import PlatformVariant, PlatformVariantRevision
from app.models.product import Product
from app.services.platform_content import PlatformGenerationResult
from app.services.processing_admission import get_processing_admission

client = post_client
CONTENT = {"headline": "New headline", "body": "New caption", "hashtags": ["buyora"]}


def new_post(client):
    product_id = product(client)
    post = client.post(
        f"/products/{product_id}/posts", json=VERSION, headers=ORIGIN
    ).json()
    return product_id, post


def test_request_manual_variant_and_revisions(client):
    client, _ = client
    login(client, "seller@example.com")
    _, post = new_post(client)
    path = f"/posts/{post['id']}/variants"
    request = {
        "source_version_id": post["latest_version"]["id"],
        "platform": "instagram",
        "preferences": "short",
    }
    admission = FakeProcessingAdmission()
    client.app.dependency_overrides[get_processing_admission] = lambda: admission  # noqa: B023
    pending = client.post(path, json=request, headers=ORIGIN)
    assert pending.status_code == 201
    assert (
        pending.json()["status"] == "pending"
        and pending.json()["processing_available"] is True
    )
    assert pending.json()["latest_revision"] is None
    assert admission.accepted == [("platform_generation", pending.json()["id"])]
    client.app.dependency_overrides.pop(get_processing_admission)
    assert client.get(f"{path}/{pending.json()['id']}").json()["status"] == "pending"
    created = client.post(path, json=request | {"content": CONTENT}, headers=ORIGIN)
    assert created.status_code == 201 and created.json()["status"] == "ready"
    item = created.json()
    assert item["latest_revision"]["revision_number"] == 1
    variant_path = f"{path}/{item['id']}"
    assert client.get(variant_path).json()["latest_revision"]["body"] == "New caption"
    revision = client.post(
        variant_path + "/revisions",
        json=CONTENT | {"body": "Updated caption"},
        headers=ORIGIN,
    )
    assert revision.status_code == 201 and revision.json()["revision_number"] == 2
    versions = client.get(variant_path + "/revisions").json()
    assert [r["body"] for r in versions] == ["Updated caption", "New caption"]
    assert client.get(f"/posts/{post['id']}").json() == post
    listed = client.get(path, params={"limit": 1, "platform": "instagram"}).json()
    assert listed["total"] == 2 and listed["items"][0]["id"] == item["id"]


def test_ownership_invalid_requests_and_post_deletion(client):
    client, engine = client
    assert client.get("/posts/1/variants").status_code == 401
    login(client, "one@example.com")
    product_id, post = new_post(client)
    _, other = new_post(client)
    path = f"/posts/{post['id']}/variants"
    data = {
        "source_version_id": post["latest_version"]["id"],
        "platform": "tiktok",
        "content": CONTENT,
    }
    assert (
        client.post(
            path, json=data | {"platform": "youtube"}, headers=ORIGIN
        ).status_code
        == 422
    )
    assert (
        client.post(
            path,
            json=data | {"source_version_id": other["latest_version"]["id"]},
            headers=ORIGIN,
        ).status_code
        == 404
    )
    assert (
        client.post(
            path, json=data, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    variant = client.post(path, json=data, headers=ORIGIN).json()
    variant_path = f"{path}/{variant['id']}"
    login(client, "two@example.com")
    assert client.get(path).status_code == 404
    assert client.get(variant_path).status_code == 404
    assert (
        client.post(
            variant_path + "/revisions", json=CONTENT, headers=ORIGIN
        ).status_code
        == 404
    )
    client.post(
        "/auth/login",
        json={"email": "one@example.com", "password": "password123"},
        headers=ORIGIN,
    )
    assert client.delete(f"/posts/{post['id']}", headers=ORIGIN).status_code == 204
    assert client.get(variant_path).status_code == 404
    with engine.connect() as conn:
        assert (
            conn.execute(
                select(PlatformVariant.id).where(PlatformVariant.id == variant["id"])
            ).first()
            is None
        )
        assert (
            conn.execute(
                select(PlatformVariantRevision.id).where(
                    PlatformVariantRevision.variant_id == variant["id"]
                )
            ).first()
            is None
        )
    with engine.begin() as conn:
        conn.execute(
            Product.__table__.update()
            .where(Product.id == product_id)
            .values(deleted_at=datetime.now(UTC))
        )
    assert client.get(path).status_code == 404


def test_invalid_ai_output_rejected():
    with pytest.raises(ValidationError):
        PlatformGenerationResult.model_validate(
            {"content": {"headline": "", "body": "x"}}
        )
    with pytest.raises(ValidationError):
        PlatformGenerationResult.model_validate(
            {"content": CONTENT, "unknown": "value"}
        )


def test_platform_migration_offline_sql_and_downgrade(monkeypatch):
    from io import StringIO
    from runpy import run_path

    from alembic import command
    from alembic.config import Config

    from app.core.config import BACKEND_DIR

    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:test@localhost/postgres")
    output = StringIO()
    config = Config(str(BACKEND_DIR / "alembic.ini"), output_buffer=output)
    command.upgrade(config, "0013:0014", sql=True)
    sql = output.getvalue()
    assert "CREATE TABLE public.platform_variants" in sql
    assert "CREATE TABLE public.platform_variant_revisions" in sql
    assert "ON DELETE CASCADE" in sql
    migration = run_path(
        str(BACKEND_DIR / "migrations/versions/0014_platform_variants.py")
    )
    with pytest.raises(RuntimeError, match="manual review"):
        migration["downgrade"]()


def test_unavailable_generation_leaves_no_variant_manual_still_works(client):
    from sqlalchemy import func

    client, engine = client
    login(client, "seller@example.com")
    _, post = new_post(client)
    path = f"/posts/{post['id']}/variants"
    data = {"source_version_id": post["latest_version"]["id"], "platform": "facebook"}
    client.app.state.platform_processing_available = True
    rejected = client.post(path, json=data, headers=ORIGIN)
    assert rejected.status_code == 503
    assert rejected.json()["detail"] == "Platform generation service is not configured"
    with engine.connect() as conn:
        assert (
            conn.execute(select(func.count()).select_from(PlatformVariant)).scalar_one()
            == 0
        )
    manual = client.post(path, json=data | {"content": CONTENT}, headers=ORIGIN)
    assert manual.status_code == 201 and manual.json()["status"] == "ready"
    item = f"{path}/{manual.json()['id']}"
    assert (
        client.post(item + "/revisions", json=CONTENT, headers=ORIGIN).status_code
        == 201
    )
    assert len(client.get(item + "/revisions").json()) == 2
    assert client.get(item).status_code == 200


def test_platform_dispatch_failure_rolls_back(client):
    from sqlalchemy import func

    client, engine = client
    login(client, "seller@example.com")
    _, post = new_post(client)
    path = f"/posts/{post['id']}/variants"
    data = {"source_version_id": post["latest_version"]["id"], "platform": "tiktok"}
    for admission in (
        FakeProcessingAdmission(ready=False),
        FakeProcessingAdmission(fail_enqueue=True),
    ):
        client.app.dependency_overrides[get_processing_admission] = lambda: admission  # noqa: B023
        assert client.post(path, json=data, headers=ORIGIN).status_code == 503
    with engine.connect() as conn:
        assert (
            conn.execute(select(func.count()).select_from(PlatformVariant)).scalar_one()
            == 0
        )


def test_configured_mock_generation_can_complete(client):
    from sqlalchemy.orm import Session

    client, engine = client
    login(client, "seller@example.com")
    _, post = new_post(client)
    admission = FakeProcessingAdmission()
    client.app.dependency_overrides[get_processing_admission] = lambda: admission
    path = f"/posts/{post['id']}/variants"
    result = client.post(
        path,
        json={
            "source_version_id": post["latest_version"]["id"],
            "platform": "whatsapp",
        },
        headers=ORIGIN,
    )
    assert result.status_code == 201
    variant_id = result.json()["id"]
    assert admission.accepted == [("platform_generation", variant_id)]
    # Simulate a worker using test-only content; no production provider is wired.
    with Session(engine) as db:
        variant = db.get(PlatformVariant, variant_id)
        variant.status = "ready"
        db.add(
            PlatformVariantRevision(
                variant_id=variant_id, revision_number=1, origin="ai", **CONTENT
            )
        )
        db.commit()
    saved = client.get(f"{path}/{variant_id}").json()
    assert saved["status"] == "ready"
    assert saved["processing_available"] is True
    assert saved["latest_revision"]["body"] == CONTENT["body"]
