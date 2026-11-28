from datetime import UTC, datetime, timedelta

import pytest
from processing_fakes import FakeProcessingAdmission
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_platform_variants import CONTENT, new_post
from test_products import ORIGIN, login_as
from test_products import client as product_client

from app.models import AIRequestReservation, MarketAnalysis, PlatformVariant
from app.services.processing_admission import get_processing_admission

client = product_client


def prepare(client):
    login_as(client, "limits@example.com")
    product, post = new_post(client)
    admission = FakeProcessingAdmission()
    client.app.dependency_overrides[get_processing_admission] = lambda: admission
    evidence = client.post(
        "/competitor-evidence",
        json={
            "competitor_name": "Example",
            "product_name": "Mouse",
            "observed_at": "2025-01-01",
            "source_url": "https://example.com/item",
            "source_note": "Seller-entered listing",
        },
        headers=ORIGIN,
    ).json()["id"]
    return product, post, evidence, admission


def generate(client, post):
    return client.post(
        f"/posts/{post['id']}/variants",
        json={
            "source_version_id": post["latest_version"]["id"],
            "platform": "facebook",
        },
        headers=ORIGIN,
    )


def test_optional_ai_rate_limit_is_shared_and_transactional(client):
    client, engine = client
    product, post, evidence, admission = prepare(client)
    client.app.state.settings.phase2_ai_requests_per_minute = 1
    assert generate(client, post).status_code == 201
    rejected = client.post(
        f"/products/{product}/market-analyses",
        json={
            "competitor_evidence_ids": [evidence],
        },
        headers=ORIGIN,
    )
    assert rejected.status_code == 429
    assert 1 <= int(rejected.headers["Retry-After"]) <= 60
    assert "rate limit" in rejected.json()["detail"]
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(AIRequestReservation)) == 1
        assert db.scalar(select(func.count()).select_from(MarketAnalysis)) == 0
    assert len(admission.accepted) == 1
    # Seller-authored content does not reserve AI budget.
    manual = client.post(
        f"/posts/{post['id']}/variants",
        json={
            "source_version_id": post["latest_version"]["id"],
            "platform": "facebook",
            "content": CONTENT,
        },
        headers=ORIGIN,
    )
    assert manual.status_code == 201


def test_daily_budget_and_window_reset(client):
    client, engine = client
    _, post, _, _ = prepare(client)
    settings = client.app.state.settings
    settings.phase2_ai_daily_token_budget = (
        settings.phase2_ai_max_input_tokens + settings.phase2_ai_max_output_tokens
    )
    assert generate(client, post).status_code == 201
    rejected = generate(client, post)
    assert rejected.status_code == 429
    assert "Daily AI token budget" in rejected.json()["detail"]
    with Session(engine) as db:
        row = db.scalar(select(AIRequestReservation))
        row.created_at = datetime.now(UTC) - timedelta(days=1)
        db.commit()
    assert generate(client, post).status_code == 201


@pytest.mark.parametrize("mode", ["unavailable", "dispatch_failure", "oversize"])
def test_rejected_requests_never_consume_allowance(client, mode):
    client, engine = client
    _, post, _, admission = prepare(client)
    if mode == "unavailable":
        admission.ready = False
    elif mode == "dispatch_failure":
        admission.fail_enqueue = True
    else:
        client.app.state.settings.phase2_ai_max_input_tokens = 1
    assert generate(client, post).status_code == (422 if mode == "oversize" else 503)
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(AIRequestReservation)) == 0
        assert db.scalar(select(func.count()).select_from(PlatformVariant)) == 0


def test_market_flag_alone_cannot_accept_work(client):
    client, engine = client
    product, _, evidence, _ = prepare(client)
    client.app.dependency_overrides.pop(get_processing_admission)
    client.app.state.market_analysis_processing_available = True
    response = client.post(
        f"/products/{product}/market-analyses",
        json={
            "competitor_evidence_ids": [evidence],
        },
        headers=ORIGIN,
    )
    assert response.status_code == 503
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(MarketAnalysis)) == 0
