from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from test_products import ORIGIN, login_as
from test_products import client as product_client

from app.models.competitor_evidence import CompetitorEvidence

client = product_client


def sample(**values):
    return {
        "competitor_name": "  TechZone  ",
        "product_name": " Mouse ",
        "observed_at": "2025-01-01",
    } | values


def test_provenance_round_trip_and_validation(client):
    client, _ = client
    login_as(client, "sources@example.com")
    created = client.post(
        "/competitor-evidence",
        json=sample(
            source_url="https://example.com/listing",
            source_note=" Offline price check ",
        ),
        headers=ORIGIN,
    )
    assert created.status_code == 201
    item = created.json()
    assert item["source_note"] == "Offline price check"
    path = f"/competitor-evidence/{item['id']}"
    assert client.get(path).json()["source_url"] == "https://example.com/listing"
    for url in (
        "javascript:alert(1)",
        "https://user:password@example.com/item",
        "file:///item",
    ):
        assert (
            client.post(
                "/competitor-evidence", json=sample(source_url=url), headers=ORIGIN
            ).status_code
            == 422
        )
        assert (
            client.patch(path, json={"source_url": url}, headers=ORIGIN).status_code
            == 422
        )
    cleared = client.patch(path, json={"source_url": None}, headers=ORIGIN)
    assert cleared.status_code == 200 and cleared.json()["source_url"] is None


def test_crud_filters_and_soft_delete(client):
    client, engine = client
    assert client.get("/competitor-evidence").status_code == 401
    login_as(client, "one@example.com")
    product = client.post(
        "/products",
        json={"name": "Item", "category": "Tech", "price": 10},
        headers=ORIGIN,
    ).json()
    first = client.post(
        "/competitor-evidence",
        json=sample(
            product_id=product["id"],
            price="12.50",
            currency="BDT",
            platform="facebook",
            competitor_description="details",
        ),
        headers=ORIGIN,
    )
    assert first.status_code == 201
    evidence = first.json()
    assert (
        evidence["competitor_name"] == "TechZone"
        and evidence["product_name"] == "Mouse"
    )
    second = client.post(
        "/competitor-evidence",
        json=sample(
            competitor_name="Other", product_name="Keyboard", observed_at="2025-02-01"
        ),
        headers=ORIGIN,
    ).json()
    assert second["competitor_description"] is None
    listing = client.get("/competitor-evidence", params={"limit": 1}).json()
    assert listing["total"] == 2 and listing["items"][0]["id"] == second["id"]
    assert (
        client.get("/competitor-evidence", params={"offset": 1}).json()["items"][0][
            "id"
        ]
        == evidence["id"]
    )
    for params in (
        {"q": "TECHzone"},
        {"q": "mOuSe"},
        {"product_id": product["id"]},
        {"platform": "FACEBOOK"},
        {"observed_at": "2025-01-01"},
        {"observed_from": "2024-01-01", "observed_to": "2025-01-01"},
    ):
        assert [
            x["id"]
            for x in client.get("/competitor-evidence", params=params).json()["items"]
        ] == [evidence["id"]]
    path = f"/competitor-evidence/{evidence['id']}"
    assert client.get(path).json()["id"] == evidence["id"]
    changed = client.patch(
        path,
        json={"competitor_description": None, "price": None, "currency": None},
        headers=ORIGIN,
    )
    assert (
        changed.status_code == 200
        and changed.json()["competitor_description"] is None
        and changed.json()["product_name"] == "Mouse"
    )
    assert (
        client.delete(f"/products/{product['id']}", headers=ORIGIN).status_code == 204
    )
    assert client.get(path).status_code == 200
    assert client.delete(path, headers=ORIGIN).status_code == 204
    assert client.get(path).status_code == 404
    with engine.connect() as connection:
        assert (
            connection.execute(
                select(CompetitorEvidence.deleted_at).where(
                    CompetitorEvidence.id == evidence["id"]
                )
            ).scalar_one()
            is not None
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"competitor_name": " "},
        {"product_name": None},
        {"price": "-1", "currency": "BDT"},
        {"price": "1"},
        {"currency": "BDT"},
        {"price": "1", "currency": "bdt"},
        {"price": "NaN", "currency": "BDT"},
        {"price": "1.234", "currency": "BDT"},
        {"observed_at": (datetime.now(UTC).date() + timedelta(days=1)).isoformat()},
        {"seller_id": 1},
        {"competitor_name": "a" * 201},
    ],
)
def test_invalid_input(client, changes):
    client, _ = client
    login_as(client, "one@example.com")
    assert (
        client.post(
            "/competitor-evidence", json=sample(**changes), headers=ORIGIN
        ).status_code
        == 422
    )


def test_ownership_product_validation_and_csrf(client):
    client, _ = client
    login_as(client, "one@example.com")
    product_id = client.post(
        "/products",
        json={"name": "Item", "category": "Tech", "price": 10},
        headers=ORIGIN,
    ).json()["id"]
    evidence_id = client.post(
        "/competitor-evidence", json=sample(product_id=product_id), headers=ORIGIN
    ).json()["id"]
    path = f"/competitor-evidence/{evidence_id}"
    assert client.patch(path, json={"price": "5"}, headers=ORIGIN).status_code == 422
    assert (
        client.patch(path, json={"competitor_name": None}, headers=ORIGIN).status_code
        == 422
    )
    assert (
        client.patch(
            path, json={"notes": "x"}, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    login_as(client, "two@example.com")
    assert client.get("/competitor-evidence").json()["total"] == 0
    assert client.get(path).status_code == 404
    assert client.patch(path, json={"notes": "x"}, headers=ORIGIN).status_code == 404
    assert client.delete(path, headers=ORIGIN).status_code == 404
    for value in (product_id, 99999):
        assert (
            client.post(
                "/competitor-evidence", json=sample(product_id=value), headers=ORIGIN
            ).status_code
            == 404
        )
    own_product = client.post(
        "/products",
        json={"name": "Item", "category": "Tech", "price": 10},
        headers=ORIGIN,
    ).json()["id"]
    assert client.delete(f"/products/{own_product}", headers=ORIGIN).status_code == 204
    assert (
        client.post(
            "/competitor-evidence", json=sample(product_id=own_product), headers=ORIGIN
        ).status_code
        == 404
    )


def test_competitor_migration_dispatches_safely(monkeypatch):
    from runpy import run_path
    from unittest.mock import Mock

    from app.core.config import BACKEND_DIR

    migration = run_path(
        str(BACKEND_DIR / "migrations/versions/0012_competitor_evidence.py")
    )
    upgrade = migration["upgrade"]
    globals_ = upgrade.__globals__
    inspector = Mock()
    monkeypatch.setattr(globals_["context"], "is_offline_mode", lambda: False)
    monkeypatch.setattr(globals_["op"], "get_bind", lambda: object())
    monkeypatch.setattr(globals_["sa"], "inspect", lambda _: inspector)
    monkeypatch.setattr(globals_["op"], "execute", lambda _: None)
    create = Mock()
    validate = Mock()
    monkeypatch.setitem(globals_, "create_table", create)
    monkeypatch.setitem(globals_, "validate_existing", validate)
    inspector.has_table.return_value = False
    upgrade()
    create.assert_called_once()
    inspector.has_table.return_value = True
    upgrade()
    validate.assert_called_once_with(inspector)
    validate.side_effect = RuntimeError("incompatible")
    with pytest.raises(RuntimeError, match="incompatible"):
        upgrade()
    create.assert_called_once()


def test_competitor_migration_rejects_incompatible_existing_table():
    from runpy import run_path
    from unittest.mock import Mock

    from app.core.config import BACKEND_DIR

    migration = run_path(
        str(BACKEND_DIR / "migrations/versions/0012_competitor_evidence.py")
    )
    inspector = Mock()
    inspector.get_columns.return_value = []
    with pytest.raises(RuntimeError, match="missing required columns"):
        migration["validate_existing"](inspector)
