from io import StringIO
from runpy import run_path

import pytest
from alembic import command
from alembic.config import Config
from processing_fakes import FakeProcessingAdmission
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from test_products import ORIGIN, login_as
from test_products import client as product_client

from app.core.config import BACKEND_DIR
from app.models.market_analysis import MarketAnalysis
from app.services.market_analysis import process_market_analysis
from app.services.processing_admission import get_processing_admission

client = product_client


def create_product(client, name="Mouse"):
    return client.post(
        "/products",
        json={
            "name": name,
            "category": "Devices",
            "price": "1000.00",
            "features": ["Rechargeable"],
        },
        headers=ORIGIN,
    ).json()["id"]


def evidence(client, **extra):
    data = {
        "competitor_name": "Seller",
        "product_name": "Mouse",
        "price": "950.00",
        "currency": "BDT",
        "observed_at": "2025-01-01",
    } | extra
    return client.post("/competitor-evidence", json=data, headers=ORIGIN).json()["id"]


def test_unavailable_and_snapshot_history(client):
    client, _ = client
    login_as(client, "one@example.com")
    product = create_product(client)
    competitor = evidence(
        client,
        source_url="https://example.com/original",
        source_note="Seller's manual observation",
    )
    other_product = create_product(client, "Other")
    foreign_product_link = evidence(client, product_id=other_product, currency="USD")
    path = f"/products/{product}/market-analyses"
    data = {"competitor_evidence_ids": [competitor, foreign_product_link]}
    assert client.post(path, json=data, headers=ORIGIN).status_code == 503
    assert client.get(path).json()["total"] == 0
    # Simulate installation of a future durable worker, not an AI provider.
    client.app.dependency_overrides[get_processing_admission] = FakeProcessingAdmission
    created = client.post(path, json=data, headers=ORIGIN)
    assert created.status_code == 202
    item = created.json()
    assert item["status"] == "pending" and item["analysis_result"] is None
    assert item["input_snapshot"]["product"]["price"] == "1000.00"
    assert item["input_snapshot"]["competitors"][0]["observed_at"] == "2025-01-01"
    assert (
        item["input_snapshot"]["competitors"][0]["source_url"]
        == "https://example.com/original"
    )
    assert [x["comparison"] for x in item["price_observations"]] == [
        "lower",
        "not_comparable",
    ]
    client.patch(f"/products/{product}", json={"name": "Changed"}, headers=ORIGIN)
    client.patch(
        f"/competitor-evidence/{competitor}",
        json={"competitor_name": "Changed", "source_url": "https://example.com/new"},
        headers=ORIGIN,
    )
    client.delete(f"/competitor-evidence/{foreign_product_link}", headers=ORIGIN)
    saved = client.get(f"{path}/{item['id']}").json()
    assert saved["input_snapshot"] == item["input_snapshot"]
    assert client.get(path, params={"limit": 1}).json()["total"] == 1
    assert client.post(path, json=data, headers=ORIGIN).status_code == 404


def test_validation_isolation_and_origin(client):
    client, _ = client
    assert client.get("/products/1/market-analyses").status_code == 401
    login_as(client, "one@example.com")
    product = create_product(client)
    competitor = evidence(client)
    path = f"/products/{product}/market-analyses"
    for ids in ([], [competitor, competitor], list(range(1, 22)), [0]):
        assert (
            client.post(
                path, json={"competitor_evidence_ids": ids}, headers=ORIGIN
            ).status_code
            == 422
        )
    assert (
        client.post(
            path, json={"competitor_evidence_ids": [9999]}, headers=ORIGIN
        ).status_code
        == 404
    )
    assert (
        client.post(
            path,
            json={"competitor_evidence_ids": [competitor]},
            headers={"Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    login_as(client, "two@example.com")
    own_product = create_product(client)
    assert client.get(path).status_code == 404
    assert (
        client.post(
            f"/products/{own_product}/market-analyses",
            json={"competitor_evidence_ids": [competitor]},
            headers=ORIGIN,
        ).status_code
        == 404
    )
    assert client.delete(f"/products/{own_product}", headers=ORIGIN).status_code == 204
    assert (
        client.post(
            f"/products/{own_product}/market-analyses",
            json={"competitor_evidence_ids": [competitor]},
            headers=ORIGIN,
        ).status_code
        == 404
    )


def test_mock_processing_valid_invalid_and_grounding(client):
    client, engine = client
    login_as(client, "one@example.com")
    product = create_product(client)
    competitor = evidence(client)
    client.app.dependency_overrides[get_processing_admission] = FakeProcessingAdmission
    path = f"/products/{product}/market-analyses"

    def create():
        return client.post(
            path, json={"competitor_evidence_ids": [competitor]}, headers=ORIGIN
        ).json()["id"]

    result = {
        "feature_comparison": "Seller-provided descriptions differ.",
        "offer_comparison": "No offer was supplied.",
        "competitive_strengths": [],
        "competitive_weaknesses": [],
        "marketing_recommendations": [],
        "limitations": ["Seller-provided information is unverified."],
    }

    class Analyzer:
        def analyze(self, data):
            return result

    factory = sessionmaker(bind=engine)
    first = create()
    assert process_market_analysis(
        factory, first, Analyzer(), lambda inputs, output: True
    )
    assert not process_market_analysis(
        factory, first, Analyzer(), lambda inputs, output: True
    )
    assert client.get(f"{path}/{first}").json()["status"] == "completed"
    second = create()
    assert process_market_analysis(
        factory, second, Analyzer(), lambda inputs, output: False
    )
    failed = client.get(f"{path}/{second}").json()
    assert failed["status"] == "failed" and failed["analysis_result"] is None
    result.pop("limitations")
    third = create()
    process_market_analysis(factory, third, Analyzer(), lambda inputs, output: True)
    assert client.get(f"{path}/{third}").json()["status"] == "failed"
    with engine.connect() as conn:
        assert len(conn.execute(select(MarketAnalysis.id)).all()) == 3


def test_market_migration_offline(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:test@localhost/postgres")
    output = StringIO()
    command.upgrade(
        Config(str(BACKEND_DIR / "alembic.ini"), output_buffer=output),
        "0014:0015",
        sql=True,
    )
    assert "CREATE TABLE public.market_analyses" in output.getvalue()
    migration = run_path(
        str(BACKEND_DIR / "migrations/versions/0015_market_analyses.py")
    )
    with pytest.raises(RuntimeError, match="manual review"):
        migration["downgrade"]()


def test_missing_price_is_json_null(client):
    client, _ = client
    login_as(client, "seller@example.com")
    product = create_product(client)
    competitor = evidence(client, price=None, currency=None)
    client.app.dependency_overrides[get_processing_admission] = FakeProcessingAdmission
    response = client.post(
        f"/products/{product}/market-analyses",
        json={"competitor_evidence_ids": [competitor]},
        headers=ORIGIN,
    )
    assert response.status_code == 202
    observation = response.json()["price_observations"][0]
    assert (
        observation["price"] is None and observation["comparison"] == "not_comparable"
    )


def test_phase_two_openapi_documents_session_and_errors(client):
    client, _ = client
    schema = client.get("/openapi.json").json()
    assert schema["components"]["securitySchemes"]["SellerSession"]["in"] == "cookie"
    path = schema["paths"]["/products/{product_id}/market-analyses"]["post"]
    assert path["security"] == [{"SellerSession": []}]
    assert {"202", "401", "403", "404", "503"} <= set(path["responses"])
    image = schema["paths"]["/products/{product_id}/images/{image_id}/analyses"]["post"]
    assert (
        "202" in image["responses"] and "processing_available" in image["description"]
    )
