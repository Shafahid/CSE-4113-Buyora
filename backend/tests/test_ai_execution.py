import asyncio
from datetime import timedelta
from uuid import uuid4

from test_execution import ORIGIN, process, sign_in, start, verdict

from app.models import PersonaAdaptation
from app.services.llm import ModelFailure
from app.services.persona_engine import contextual_profiles
from app.services.persona_jobs import claim_adaptation, execute_adaptation
from app.services.simulation_runs import now

pytest_plugins = ("test_execution",)


def test_adaptation_cache_fresh_idempotency_and_ownership(execution):
    client, factory, settings, payload, _ = execution
    context = client.post(
        "/persona-adaptations", json={**payload, "mode": "context"}, headers=ORIGIN
    )
    assert context.status_code == 202
    assert context.json()["source"] == "context"
    assert all("Canvas bag" in p["context"] for p in context.json()["profiles"])
    assert claim_adaptation(factory) is None
    data = {**payload, "mode": "ai"}
    first = client.post("/persona-adaptations", json=data, headers=ORIGIN).json()
    assert first["status"] == "queued"
    repeated = client.post(
        "/persona-adaptations",
        json={**data, "request_id": str(uuid4())},
        headers=ORIGIN,
    ).json()
    assert repeated["id"] == first["id"] and repeated["cache_hit"]
    calls = []

    async def generate(_, inputs):
        calls.append(inputs)
        return contextual_profiles(inputs), {"input_tokens": 15, "output_tokens": 20}

    job = claim_adaptation(factory)
    asyncio.run(execute_adaptation(factory, settings, *job, evaluator=generate))
    finished = client.get(f"/persona-adaptations/{first['id']}").json()
    assert finished["status"] == "completed" and len(finished["profiles"]) == 3
    assert len(calls) == 1 and claim_adaptation(factory) is None
    assert (
        client.post("/persona-adaptations", json=data, headers=ORIGIN).json()["id"]
        == first["id"]
    )
    assert (
        client.post(
            "/persona-adaptations", json={**data, "language": "bn"}, headers=ORIGIN
        ).status_code
        == 409
    )
    fresh_data = {**data, "request_id": str(uuid4()), "fresh": True}
    fresh = client.post("/persona-adaptations", json=fresh_data, headers=ORIGIN).json()
    assert fresh["id"] != first["id"]
    assert (
        client.post("/persona-adaptations", json=fresh_data, headers=ORIGIN).json()[
            "id"
        ]
        == fresh["id"]
    )
    sign_in(client, "other@example.com")
    assert client.get(f"/persona-adaptations/{first['id']}").status_code == 404
    assert (
        client.post("/persona-adaptations", json=fresh_data, headers=ORIGIN).status_code
        == 404
    )


def test_adaptation_provider_failure_and_interruption_fall_back_without_rebilling(
    execution,
):
    client, factory, settings, payload, _ = execution
    first = client.post(
        "/persona-adaptations", json={**payload, "mode": "ai"}, headers=ORIGIN
    ).json()

    async def unavailable(*args):
        raise ModelFailure("provider_auth")

    job = claim_adaptation(factory)
    asyncio.run(execute_adaptation(factory, settings, *job, evaluator=unavailable))
    result = client.get(f"/persona-adaptations/{first['id']}").json()
    assert result["status"] == "fallback" and result["error_code"] == "provider_auth"
    assert len(result["profiles"]) == 3
    fresh = client.post(
        "/persona-adaptations",
        json={**payload, "request_id": str(uuid4()), "mode": "ai", "fresh": True},
        headers=ORIGIN,
    ).json()
    assert claim_adaptation(factory)
    with factory() as db:
        db.get(PersonaAdaptation, fresh["id"]).lease_until = now() - timedelta(
            seconds=1
        )
        db.commit()
    assert claim_adaptation(factory) is None
    result = client.get(f"/persona-adaptations/{fresh['id']}").json()
    assert result["source"] == "fallback" and result["error_code"] == "interrupted"


def test_mixed_ai_fallback_is_cached_and_explicit_retry_preserves_other_outputs(
    execution,
):
    client, factory, settings, payload, _ = execution
    settings.llm_fallback_enabled = True
    settings.llm_max_attempts = 1
    first = start(client, payload)
    seen = []

    async def partial(_, inputs, profile):
        seen.append(profile["id"])
        if profile["id"] != payload["personas"][0]["id"]:
            raise ModelFailure("provider_unavailable")
        return verdict(), {"input_tokens": 10, "output_tokens": 20}

    process(factory, settings, partial)
    result = client.get(f"/simulation-runs/{first['id']}").json()
    report = result["report"]
    assert result["status"] == "completed" and report["fallbackCount"] == 2
    assert (
        client.post(
            f"/simulation-runs/{first['id']}/retry-failed",
            headers=ORIGIN,
            json={"request_id": str(uuid4())},
        ).status_code
        == 409
    )
    assert report["usage"]["modelCalls"] == 3
    assert report["usage"]["outputTokens"] == 20
    assert start(client, {**payload, "request_id": str(uuid4())})["id"] == first["id"]
    assert len(seen) == 3
    retry = result["evaluations"][1]
    assert retry["can_retry"]
    client.post(
        f"/simulation-runs/{first['id']}/retry",
        json={"evaluation_id": retry["id"]},
        headers=ORIGIN,
    )
    process(factory, settings)
    updated = client.get(f"/simulation-runs/{first['id']}").json()
    assert updated["report"]["fallbackCount"] == 1
    assert updated["evaluations"][0]["output"] == result["evaluations"][0]["output"]
    assert updated["evaluations"][2]["output"] == result["evaluations"][2]["output"]


def test_budget_stops_model_calls_and_supplies_labeled_fallback(execution):
    client, factory, settings, payload, _ = execution
    settings.llm_fallback_enabled = True
    settings.simulation_max_model_calls = 1
    settings.simulation_concurrency = 1
    run = start(client, payload)
    seen = []

    async def evaluate(*args):
        seen.append(True)
        return verdict(), {"input_tokens": 10, "output_tokens": 20}

    process(factory, settings, evaluate)
    result = client.get(f"/simulation-runs/{run['id']}").json()
    assert len(seen) == 1 and result["report"]["fallbackCount"] == 2
    settings.simulation_token_budget = 1000
    run = start(client, {**payload, "request_id": str(uuid4())})
    process(factory, settings, evaluate)
    result = client.get(f"/simulation-runs/{run['id']}").json()
    assert len(seen) == 1 and result["report"]["fallbackCount"] == 3
    assert result["report"]["usage"]["modelCalls"] == 0


def test_no_provider_config_can_complete_with_fallback_and_grounded_server_revision(
    execution,
):
    client, factory, settings, payload, product = execution
    settings.llm_fallback_enabled = True
    settings.token_bd_api_key = None
    first = start(client, payload)
    process(factory, settings, evaluator=None)
    result = client.get(f"/simulation-runs/{first['id']}").json()
    assert result["report"]["fallbackCount"] == 3
    client.patch(
        f"/products/{product['id']}",
        headers=ORIGIN,
        json={"delivery_info": "Changed later"},
    )
    path = f"/simulation-runs/{first['id']}/revise"
    response = client.post(path, headers=ORIGIN, json={"applied": ["delivery"]})
    assert response.status_code == 200, response.text
    body = response.json()["report"]["revised"]
    assert "Dhaka in 3 days" in body and "Changed later" not in body
    assert (
        client.post(
            path, headers=ORIGIN, json={"applied": ["invented-offer"]}
        ).status_code
        == 422
    )
    sign_in(client, "other@example.com")
    assert client.post(path, headers=ORIGIN, json={"applied": []}).status_code == 404
