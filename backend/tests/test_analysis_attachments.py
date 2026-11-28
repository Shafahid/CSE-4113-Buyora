from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import null
from test_execution import ORIGIN, process, start

from app.models import MarketAnalysis

pytest_plugins = ("test_execution",)


def completed_market(factory, seller_id, product_id):
    with factory() as db:
        row = MarketAnalysis(
            seller_id=seller_id,
            product_id=product_id,
            language="en",
            status="completed",
            completed_at=datetime.now(UTC),
            input_snapshot={
                "language": "en",
                "product": {
                    "id": product_id,
                    "name": "Canvas bag",
                    "category": "Accessories",
                    "price": "120",
                    "currency": "BDT",
                    "description": None,
                    "features": [],
                },
                "competitors": [
                    {
                        "id": 1,
                        "product_id": None,
                        "competitor_name": "Example seller",
                        "product_name": "Bag",
                        "competitor_description": None,
                        "category": None,
                        "price": "125",
                        "currency": "BDT",
                        "offer": None,
                        "platform": "facebook",
                        "observed_at": "2025-01-01",
                        "notes": None,
                        "source_url": "https://example.com/bag",
                        "source_note": "Manually supplied",
                    }
                ],
            },
            analysis_result={
                "feature_comparison": "Example only",
                "offer_comparison": "No offers",
                "competitive_strengths": [],
                "competitive_weaknesses": [],
                "marketing_recommendations": [],
                "limitations": ["Unverified"],
            },
        )
        db.add(row)
        db.commit()
        return row.id


def test_report_freezes_optional_analysis_and_provenance(execution):
    client, factory, settings, payload, product = execution
    seller_id = client.get("/me").json()["id"]
    analysis_id = completed_market(factory, seller_id, product["id"])
    run = start(client, payload | {"market_analysis_ids": [analysis_id]})
    with factory() as db:
        row = db.get(MarketAnalysis, analysis_id)
        row.analysis_result = {**row.analysis_result, "feature_comparison": "Changed"}
        db.commit()
    process(factory, settings)
    report = client.get(f"/simulation-runs/{run['id']}").json()["report"]
    saved = report["optionalAnalyses"]["market_comparisons"][0]
    assert saved["result"]["feature_comparison"] == "Example only"
    assert (
        saved["input_snapshot"]["competitors"][0]["source_url"]
        == "https://example.com/bag"
    )
    assert "storage_key" not in str(report["optionalAnalyses"])
    # Selecting different findings must not return the previous cached report.
    without = start(client, payload | {"request_id": str(uuid4())})
    assert without["id"] != run["id"]


def test_missing_pending_or_other_product_analysis_cannot_attach(execution):
    client, factory, _, payload, product = execution
    seller_id = client.get("/me").json()["id"]
    analysis_id = completed_market(factory, seller_id, product["id"])
    with factory() as db:
        row = db.get(MarketAnalysis, analysis_id)
        row.status, row.analysis_result = "pending", null()
        db.commit()
    for ids in ([99999], [analysis_id]):
        rejected = client.post(
            "/simulation-runs",
            json=payload
            | {
                "market_analysis_ids": ids,
            },
            headers=ORIGIN,
        )
        assert rejected.status_code == 404
    duplicate = client.post(
        "/simulation-runs",
        json=payload
        | {
            "market_analysis_ids": [analysis_id, analysis_id],
        },
        headers=ORIGIN,
    )
    assert duplicate.status_code == 422
