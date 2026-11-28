import asyncio
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, event, select

from app.main import create_app
from app.models import Base, PersonaEvaluation, SimulationCache, SimulationRun
from app.services.llm import ModelFailure, evaluate_persona
from app.services.persona_catalog import profiles
from app.services.simulation_runs import now
from app.services.simulation_worker import claim, execute_run

ORIGIN = {"Origin": "http://localhost:3000"}


@pytest.fixture
def execution(tmp_path, settings, monkeypatch):
    settings.token_bd_api_url = "https://model.example/v1"
    settings.token_bd_api_key = SecretStr("test-only-never-a-real-key")
    settings.token_bd_model = "test-model"
    settings.simulation_worker_enabled = False
    settings.llm_fallback_enabled = False
    engine = create_engine(
        f"sqlite:///{tmp_path / 'execution.db'}",
        connect_args={"check_same_thread": False},
        execution_options={"schema_translate_map": {"public": None, "buyora": None}},
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    monkeypatch.setattr("app.main.create_db_engine", lambda _: engine)
    with TestClient(create_app(settings)) as client:
        sign_in(client, "one@example.com")
        product = client.post(
            "/products",
            headers=ORIGIN,
            json={
                "name": "Canvas bag",
                "category": "Accessories",
                "price": "120.00",
                "description": "A reusable canvas bag",
                "delivery_info": "Dhaka in 3 days",
            },
        ).json()
        post = client.post(
            f"/products/{product['id']}/posts",
            headers=ORIGIN,
            json={
                "headline": "Carry your everyday essentials",
                "body": "A reusable canvas bag for your daily commute. Price BDT 120.",
                "platform": "Facebook",
            },
        ).json()
        payload = {
            "request_id": str(uuid4()),
            "post_version_id": post["latest_version"]["id"],
            "language": "en",
            "audience": {"location": "Dhaka", "age": "18–34"},
            "personas": [p.model_dump() for p in profiles()[:3]],
        }
        yield client, client.app.state.session_factory, settings, payload, product


def sign_in(client, email):
    data = {"email": email, "password": "password123", "display_name": "Seller"}
    client.post("/auth/register", json=data, headers=ORIGIN)
    assert client.post("/auth/login", json=data, headers=ORIGIN).status_code == 200


def start(client, payload):
    result = client.post("/simulation-runs", json=payload, headers=ORIGIN)
    assert result.status_code in (200, 202), result.text
    return result.json()


def verdict():
    return {
        "scores": [70, 80, 65, 60, 55, 80, 60],
        "comment": "What is the delivery charge?",
        "reason": "Delivery timing is clear, but its total cost needs confirmation.",
        "positive": "A reusable bag has a practical purpose.",
        "question": "What is the delivery charge?",
        "evidence": ["Canvas bag"],
    }


async def successful_evaluator(*args):
    return verdict(), {"input_tokens": 100, "output_tokens": 80}


def process(factory, settings, evaluator=successful_evaluator):
    job = claim(factory)
    assert job
    asyncio.run(execute_run(factory, settings, *job, evaluator=evaluator))


def test_cache_fresh_runs_and_idempotent_request(execution):
    client, factory, settings, payload, _ = execution
    first = start(client, payload)
    assert first["status"] == "queued" and not first["cache_hit"]
    assert first["updated_at"].endswith("Z")
    with factory() as db:
        saved = db.get(SimulationRun, first["id"])
        assert saved.expected_personas == len(payload["personas"])
        assert saved.stage == "queued"
    assert start(client, payload)["id"] == first["id"]
    repeated = start(client, {**payload, "request_id": str(uuid4())})
    assert repeated["id"] == first["id"] and repeated["cache_hit"]
    process(factory, settings)
    report = client.get(f"/simulation-runs/{first['id']}").json()
    assert report["status"] == "completed" and report["completed"] == 3
    assert report["report"]["source"] == "server"
    assert report["report"]["reactions"][0]["score"] == 67
    with factory() as db:
        saved = db.get(SimulationRun, first["id"])
        assert saved.expected_personas == 3
        assert saved.stage == "report_ready"
    assert start(client, {**payload, "request_id": str(uuid4())})["id"] == first["id"]
    assert claim(factory) is None  # Reopening does not enqueue model work.
    fresh_payload = {**payload, "fresh": True, "request_id": str(uuid4())}
    fresh = start(client, fresh_payload)
    assert fresh["id"] != first["id"]
    assert start(client, fresh_payload)["id"] == fresh["id"]
    assert start(client, {**payload, "request_id": str(uuid4())})["id"] == fresh["id"]
    assert client.get(f"/simulation-runs/{first['id']}").json()["status"] == "completed"


def test_input_snapshot_cache_invalidation_and_identity(execution):
    client, factory, _, payload, product = execution
    first = start(client, payload)
    changed = {**payload, "audience": {"location": "Sylhet"}}
    assert (
        client.post("/simulation-runs", headers=ORIGIN, json=changed).status_code == 409
    )
    assert start(client, {**changed, "request_id": str(uuid4())})["id"] != first["id"]
    client.patch(f"/products/{product['id']}", headers=ORIGIN, json={"price": "200.00"})
    assert start(client, {**payload, "request_id": str(uuid4())})["id"] != first["id"]
    with factory() as db:
        assert db.get(SimulationRun, first["id"]).inputs["product"]["price"] == "120.00"


def test_dynamic_personas_and_bounded_parallelism(execution):
    client, factory, settings, payload, _ = execution
    payload["personas"] = [p.model_dump() for p in profiles()]
    settings.simulation_concurrency = 2
    run = start(client, payload)
    active = 0
    peak = 0
    seen = []

    async def evaluate(_, inputs, profile):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        seen.append(profile["id"])
        await asyncio.sleep(0.04)
        active -= 1
        return verdict(), {}

    process(factory, settings, evaluate)
    assert 1 < peak <= 2
    assert len(seen) == len(set(seen)) == len(profiles())
    assert set(seen) == {profile.id for profile in profiles()}
    assert client.get(f"/simulation-runs/{run['id']}").json()["completed"] == len(
        profiles()
    )


def test_partial_failure_retry_preserves_completed_results(execution):
    client, factory, settings, payload, _ = execution
    run = start(client, payload)
    called = []

    async def evaluate(_, inputs, profile):
        called.append(profile["id"])
        if profile["id"] == "cod":
            raise ModelFailure("invalid_output")
        return verdict(), {}

    process(factory, settings, evaluate)
    partial = client.get(f"/simulation-runs/{run['id']}").json()
    assert partial["status"] == "partially_failed"
    assert partial["completed"] == 2 and partial["failed"] == 1
    with factory() as db:
        assert db.get(SimulationRun, run["id"]).stage == "report_ready_partial"
    failed = next(e for e in partial["evaluations"] if e["status"] == "failed")
    retry = {"evaluation_id": failed["id"]}
    assert (
        client.post(
            f"/simulation-runs/{run['id']}/retry", json=retry, headers=ORIGIN
        ).status_code
        == 200
    )
    client.post(f"/simulation-runs/{run['id']}/retry", json=retry, headers=ORIGIN)
    with factory() as db:
        saved = db.get(SimulationRun, run["id"])
        assert saved.expected_personas == 3
        assert saved.stage == "queued"
    retried = []

    async def retry_evaluator(_, inputs, profile):
        retried.append(profile["id"])
        return verdict(), {}

    process(factory, settings, retry_evaluator)
    assert retried == ["cod"]
    complete = client.get(f"/simulation-runs/{run['id']}").json()
    assert complete["status"] == "completed"
    assert len(called) == 3
    assert [e["attempts"] for e in complete["evaluations"]] == [1, 2, 1]


def test_bulk_retry_is_durable_and_preserves_completed_outputs(execution):
    client, factory, settings, payload, _ = execution
    run = start(client, payload)

    async def partial(_, inputs, profile):
        if profile["id"] != "budget":
            raise ModelFailure("invalid_output")
        return verdict(), {}

    process(factory, settings, partial)
    before = client.get(f"/simulation-runs/{run['id']}").json()
    assert before["completed"] == 1 and before["failed"] == 2
    url = f"/simulation-runs/{run['id']}/retry-failed"
    operation = {"request_id": str(uuid4())}
    assert client.post(url, json=operation).status_code == 403
    queued = client.post(url, json=operation, headers=ORIGIN).json()
    assert queued["status"] == "queued" and queued["started_at"] is None
    assert client.post(url, json=operation, headers=ORIGIN).json()["status"] == "queued"
    called = []

    async def still_fails(_, inputs, profile):
        called.append(profile["id"])
        raise ModelFailure("invalid_output")

    process(factory, settings, still_fails)
    assert sorted(called) == ["cod", "skeptic"]
    # Replaying after a failed retry finished must not issue more model work.
    replay = client.post(url, json=operation, headers=ORIGIN).json()
    assert replay["status"] == "partially_failed"
    assert claim(factory) is None
    assert replay["evaluations"][0]["output"] == before["evaluations"][0]["output"]
    assert replay["evaluations"][0]["attempts"] == 1
    sign_in(client, "other@example.com")
    assert (
        client.post(url, json={"request_id": str(uuid4())}, headers=ORIGIN).status_code
        == 404
    )


def test_preview_is_read_only_matches_inputs_and_checks_ownership(execution):
    client, factory, settings, payload, product = execution
    run = start(client, payload)
    process(factory, settings)
    with factory() as db:
        saved = db.get(SimulationRun, run["id"])
        post = saved.inputs["post"]
    preview = {**payload, "post": post, "product_id": product["id"]}
    url = "/simulation-runs/preview"
    match = client.post(url, json=preview, headers=ORIGIN).json()
    assert match["match"] and match["run_id"] == run["id"]
    assert match["completed"] == match["total"] == 3
    for change in (
        {
            "post": {
                **post,
                "body": "An unsaved edited caption that needs a new assessment",
            }
        },
        {"audience": {"location": "Sylhet"}},
        {"personas": payload["personas"][:2]},
    ):
        assert (
            client.post(url, json={**preview, **change}, headers=ORIGIN).json()["match"]
            is False
        )
    assert claim(factory) is None
    assert len(client.get("/simulation-runs").json()) == 1
    compact = client.get(f"/simulation-runs/{run['id']}/progress").json()
    assert "report" not in compact and compact["completed"] == 3
    sign_in(client, "other@example.com")
    assert client.post(url, json=preview, headers=ORIGIN).status_code == 404
    assert client.get(f"/simulation-runs/{run['id']}/progress").status_code == 404


def test_non_actionable_failure_is_not_queued_again(execution):
    client, factory, settings, payload, _ = execution
    run = start(client, payload)

    async def unavailable(*args):
        raise ModelFailure("provider_auth")

    process(factory, settings, unavailable)
    result = client.get(f"/simulation-runs/{run['id']}").json()
    assert result["completed"] == 0
    assert all(not row["can_retry"] for row in result["evaluations"])
    assert result["report"]["coverage"] == {"completed": 0, "total": 3, "failed": 3}
    assert (
        client.post(
            f"/simulation-runs/{run['id']}/retry-failed",
            json={"request_id": str(uuid4())},
            headers=ORIGIN,
        ).status_code
        == 409
    )
    assert claim(factory) is None


def test_worker_never_exceeds_six_paid_attempts(execution):
    client, factory, settings, payload, _ = execution
    run = start(client, payload)
    with factory() as db:
        row = db.scalar(
            select(PersonaEvaluation).where(PersonaEvaluation.run_id == run["id"])
        )
        row.attempts = 5
        db.commit()
    called = []

    async def transient(_, inputs, profile):
        called.append(profile["id"])
        raise ModelFailure("provider_unavailable", retryable=True)

    process(factory, settings, transient)
    result = client.get(f"/simulation-runs/{run['id']}").json()
    assert result["evaluations"][0]["attempts"] == 6
    assert result["evaluations"][0]["error_code"] == "retry_limit"
    assert not result["evaluations"][0]["can_retry"]
    assert called.count("budget") == 1


def test_recovery_never_silently_reissues_an_inflight_request(execution):
    client, factory, settings, payload, _ = execution
    run = start(client, payload)
    old_job = claim(factory)
    with factory() as db:
        row = db.scalar(
            select(PersonaEvaluation).where(PersonaEvaluation.run_id == run["id"])
        )
        row.status = "running"
        row.attempts = 1
        db.get(SimulationRun, run["id"]).lease_until = now() - timedelta(seconds=1)
        db.commit()
    called = []

    async def evaluate(_, inputs, profile):
        called.append(profile["id"])
        return verdict(), {}

    process(factory, settings, evaluate)
    assert called == ["cod", "skeptic"] or sorted(called) == ["cod", "skeptic"]
    result = client.get(f"/simulation-runs/{run['id']}").json()
    assert result["status"] == "partially_failed"
    assert result["evaluations"][0]["error_code"] == "interrupted"
    # A stale worker cannot overwrite a recovered run.
    asyncio.run(execute_run(factory, settings, *old_job, evaluator=evaluate))
    assert len(called) == 2


def test_run_ownership_origin_annotations_and_deletion(execution):
    client, factory, settings, payload, _ = execution
    assert client.post("/simulation-runs", json=payload).status_code == 403
    first = start(client, payload)
    assert (
        client.delete(f"/simulation-runs/{first['id']}", headers=ORIGIN).status_code
        == 409
    )
    process(factory, settings)
    changes = {"revised": "My revised caption", "applied": ["delivery"]}
    assert (
        client.patch(
            f"/simulation-runs/{first['id']}/report", headers=ORIGIN, json=changes
        ).status_code
        == 200
    )
    assert (
        client.get(f"/simulation-runs/{first['id']}").json()["report"]["revised"]
        == changes["revised"]
    )
    sign_in(client, "two@example.com")
    assert client.get("/simulation-runs").json() == []
    assert client.get(f"/simulation-runs/{first['id']}").status_code == 404
    assert (
        client.post(
            "/simulation-runs",
            headers=ORIGIN,
            json={**payload, "request_id": str(uuid4())},
        ).status_code
        == 404
    )
    sign_in(client, "one@example.com")
    assert (
        client.delete(f"/simulation-runs/{first['id']}", headers=ORIGIN).status_code
        == 204
    )
    assert client.get(f"/simulation-runs/{first['id']}").status_code == 404
    with factory() as db:
        assert not db.scalars(select(SimulationCache)).all()
        assert not db.scalars(select(PersonaEvaluation)).all()


def test_unconfigured_provider_and_persona_limit(execution):
    client, _, settings, payload, _ = execution
    settings.token_bd_api_key = None
    assert (
        client.post("/simulation-runs", headers=ORIGIN, json=payload).status_code == 503
    )
    settings.simulation_max_personas = 2
    assert (
        client.post("/simulation-runs", headers=ORIGIN, json=payload).status_code == 422
    )
    options = client.get("/simulation-options").json()
    assert options["max_personas"] == 2
    assert len(options["profiles"]) == len(profiles())


def test_model_adapter_uses_config_and_rejects_unsupported_evidence(
    execution, monkeypatch
):
    import litellm

    _, _, settings, _, _ = execution
    captured = []
    output = verdict()
    from app.services.trust_scoring import DIMENSIONS

    output["score_drivers"] = [
        {
            "dimension": dimension,
            "reason": "সংরক্ষিত পণ্যের বিবরণ যাচাই করুন।",
            "evidence": ["Canvas bag"],
        }
        for dimension in DIMENSIONS
    ]
    output.update(
        comment="দামটি ভালো মনে হচ্ছে",
        reason="বিস্তারিত তথ্য নিশ্চিত করা দরকার",
        positive="পণ্যের বিবরণ পরিষ্কার",
        question="ডেলিভারি চার্জ কত?",
    )

    async def complete(**kwargs):
        import json

        captured.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content=json.dumps(output)))
            ],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20),
        )

    monkeypatch.setattr(litellm, "acompletion", complete)
    inputs = {
        "product": {"name": "Canvas bag"},
        "post": {},
        "audience": {},
        "language": "bn",
        "checks": {},
    }
    value, usage = asyncio.run(
        evaluate_persona(settings, inputs, profiles()[0].model_dump())
    )
    assert {key: value[key] for key in output} == output
    assert usage["output_tokens"] == 20 and usage["prompt_version"]
    assert captured[0]["model"] == "openai/test-model"
    assert captured[0]["api_base"] == "https://model.example/v1"
    assert captured[0]["num_retries"] == 0
    assert captured[0]["max_tokens"] == settings.llm_max_output_tokens
    assert "bn" in captured[0]["messages"][1]["content"]
    output["evidence"] = ["Invented free delivery"]
    with pytest.raises(ModelFailure, match="invalid_output"):
        asyncio.run(evaluate_persona(settings, inputs, profiles()[0].model_dump()))


def test_truncated_response_reports_token_limit_without_retrying_invalid_json(
    execution, monkeypatch
):
    import litellm

    _, _, settings, _, _ = execution

    async def truncated(**kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="length", message=SimpleNamespace(content="")
                )
            ],
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=4096),
        )

    monkeypatch.setattr(litellm, "acompletion", truncated)
    inputs = {"product": {}, "post": {}, "audience": {}, "language": "en", "checks": {}}
    with pytest.raises(ModelFailure, match="output_truncated") as failure:
        asyncio.run(evaluate_persona(settings, inputs, profiles()[0].model_dump()))
    assert not failure.value.retryable
    assert {
        key: failure.value.metadata[key]
        for key in ("input_tokens", "output_tokens", "finish_reason", "output_limit")
    } == {
        "input_tokens": 100,
        "output_tokens": 4096,
        "finish_reason": "length",
        "output_limit": settings.llm_max_output_tokens,
    }
