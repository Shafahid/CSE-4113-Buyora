"""Opt-in integration checks on a uniquely created, disposable localhost database.

Set BUYORA_TEST_POSTGRES_URL to a localhost admin URL (database postgres).
The fixture creates/drops only buyora_test_<uuid>; it never reads backend/.env.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR
from app.models import AIRequestReservation, CompetitorEvidence, Product, User
from app.services.ai_limits import lock_ai_seller, reserve_ai_request


@pytest.fixture
def disposable_postgres(monkeypatch):
    value = os.environ.get("BUYORA_TEST_POSTGRES_URL")
    if not value:
        pytest.skip(
            "BUYORA_TEST_POSTGRES_URL is required for isolated PostgreSQL checks"
        )
    url = make_url(value)
    if url.host not in {"127.0.0.1", "localhost", "::1"} or url.database != "postgres":
        pytest.fail(
            "PostgreSQL tests require localhost and the postgres admin database"
        )
    url = url.set(drivername="postgresql+psycopg")
    database_name = "buyora_test_" + uuid4().hex
    admin = create_engine(url, isolation_level="AUTOCOMMIT", hide_parameters=True)
    engine = None
    try:
        with admin.connect() as c:
            c.execute(text(f'CREATE DATABASE "{database_name}"'))
        test_url = url.set(database=database_name)
        monkeypatch.setenv(
            "DATABASE_URL", test_url.render_as_string(hide_password=False)
        )
        monkeypatch.delenv("MIGRATION_DATABASE_URL", raising=False)
        engine = create_engine(test_url, hide_parameters=True)
        yield engine, Config(str(BACKEND_DIR / "alembic.ini"))
    finally:
        if engine is not None:
            engine.dispose()
        # Only the exact UUID database created by this fixture can be dropped.
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE IF EXISTS "{database_name}" WITH (FORCE)'))
        admin.dispose()


def test_clean_upgrade_preserves_existing_phase1_and_provenance(disposable_postgres):
    engine, config = disposable_postgres
    command.upgrade(config, "0016")
    with engine.begin() as c:
        seller_id = c.scalar(
            text(
                "INSERT INTO public.users (email, password_hash) "
                "VALUES ('migration@example.com', 'fixture-only') RETURNING id"
            )
        )
        product_id = c.scalar(
            text(
                "INSERT INTO public.products (seller_id, name, category, price) "
                "VALUES (:seller, 'Existing product', 'Example', 100) RETURNING id"
            ),
            {"seller": seller_id},
        )
        evidence_id = c.scalar(
            text(
                "INSERT INTO public.competitor_evidence "
                "(seller_id, competitor_name, product_name, observed_at) "
                "VALUES (:seller, 'Existing competitor', 'Example', CURRENT_DATE) "
                "RETURNING id"
            ),
            {"seller": seller_id},
        )
    command.upgrade(config, "head")
    with Session(engine) as db:
        assert db.get(Product, product_id).name == "Existing product"
        evidence = db.get(CompetitorEvidence, evidence_id)
        assert evidence.source_url is None and evidence.source_note is None
        evidence.source_url = "https://example.com/listing"
        evidence.source_note = "Seller-provided observation"
        db.commit()
    inspector = inspect(engine)
    assert inspector.has_table("ai_request_reservations", schema="buyora")
    assert any(
        index["column_names"] == ["seller_id", "created_at"]
        for index in inspector.get_indexes("ai_request_reservations", schema="buyora")
    )
    # Policy intentionally refuses automatic destructive downgrades.
    with pytest.raises(RuntimeError, match="manual review"):
        command.downgrade(config, "0016")
    with engine.connect() as c:
        assert (
            c.scalar(text("SELECT version_num FROM public.alembic_version")) == "0017"
        )
        assert (
            c.scalar(
                text("SELECT source_url FROM public.competitor_evidence WHERE id=:id"),
                {"id": evidence_id},
            )
            == "https://example.com/listing"
        )


def test_postgres_serializes_concurrent_ai_reservations(disposable_postgres, settings):
    engine, config = disposable_postgres
    command.upgrade(config, "head")
    with Session(engine) as db:
        user = User(email="concurrent@example.com", password_hash="fixture-only")
        db.add(user)
        db.commit()
        seller_id = user.id
    settings.phase2_ai_requests_per_minute = 1

    def accept(resource_id):
        with Session(engine) as db:
            try:
                lock_ai_seller(db, seller_id)
                reserve_ai_request(
                    db,
                    seller_id,
                    "image_analysis",
                    resource_id,
                    settings,
                    {"example": True},
                )
                db.commit()
                return "accepted"
            except HTTPException as error:
                db.rollback()
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(accept, [1, 2]))
    assert results.count("accepted") == 1 and results.count(429) == 1
    with Session(engine) as db:
        assert len(db.scalars(select(AIRequestReservation)).all()) == 1


def test_phase1_report_survives_upgrade_and_apis_still_work(
    disposable_postgres, settings, monkeypatch
):
    from fastapi.testclient import TestClient
    from test_execution import ORIGIN, process, sign_in

    from app.main import create_app
    from app.services.persona_catalog import profiles

    engine, config = disposable_postgres
    command.upgrade(config, "0016")
    monkeypatch.setattr("app.main.create_db_engine", lambda _: engine)
    with TestClient(create_app(settings)) as client:
        sign_in(client, "phase1@example.com")
        product = client.post(
            "/products",
            json={
                "name": "Existing bag",
                "category": "Accessories",
                "price": "120",
            },
            headers=ORIGIN,
        ).json()
        post = client.post(
            f"/products/{product['id']}/posts",
            json={
                "headline": "Existing headline",
                "body": "Existing caption",
                "platform": "Facebook",
            },
            headers=ORIGIN,
        ).json()
        created = client.post(
            "/simulation-runs",
            json={
                "request_id": str(uuid4()),
                "post_version_id": post["latest_version"]["id"],
                "personas": [p.model_dump() for p in profiles()[:2]],
            },
            headers=ORIGIN,
        )
        assert created.status_code == 202
        run_id = created.json()["id"]
        process(client.app.state.session_factory, settings)
        saved = client.get(f"/simulation-runs/{run_id}").json()["report"]
        assert saved["status"] == "completed"
        command.upgrade(config, "head")
        assert client.get(f"/simulation-runs/{run_id}").json()["report"] == saved
        assert client.get(f"/products/{product['id']}").json()["name"] == "Existing bag"
        assert (
            client.get(f"/posts/{post['id']}").json()["latest_version"]["body"]
            == "Existing caption"
        )
        assert client.get("/reports").status_code == 200
        # Verify migrated provenance through the authenticated API as well.
        evidence = client.post(
            "/competitor-evidence",
            json={
                "competitor_name": "Example",
                "product_name": "Bag",
                "observed_at": "2025-01-01",
                "source_url": "https://example.com/bag",
            },
            headers=ORIGIN,
        )
        assert evidence.status_code == 201
        assert evidence.json()["source_url"] == "https://example.com/bag"
