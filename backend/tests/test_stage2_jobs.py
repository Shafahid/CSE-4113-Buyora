import asyncio
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session
from test_platform_variants import CONTENT, new_post
from test_product_images import setup as image_setup
from test_products import ORIGIN, login_as
from test_products import client as product_client
from test_stage2_ai import gateway, image_bytes, image_result

from app.models import AIJob, AIRequestReservation, AIWorkerHeartbeat, PlatformVariant
from app.services.ai import jobs
from app.services.ai.platform import GroundedPlatformGenerator
from app.services.platform_content import PlatformGenerationInput

client = product_client
setup = image_setup


def prepare(client, output=None):
    login_as(client, "jobs@example.com")
    product, post = new_post(client)
    settings = client.app.state.settings
    settings.phase2_ai_enabled = True
    model, calls = gateway(
        settings, output or {"hook_id": 0, "fact_ids": ["name", "price"]}
    )
    factory = client.app.state.session_factory
    jobs.publish_heartbeat(
        factory, "worker-test", settings, ["platform_generation", "market_analysis"]
    )
    return product, post, settings, model, calls


def create(client, post):
    result = client.post(
        f"/posts/{post['id']}/variants",
        json={
            "source_version_id": post["latest_version"]["id"],
            "platform": "facebook",
        },
        headers=ORIGIN,
    )
    assert result.status_code == 201, result.text
    return result.json()


def test_real_admission_saves_dispatch_and_processes_frozen_platform_input(client):
    client, engine = client
    product, post, settings, model, calls = prepare(client)
    variant = create(client, post)
    factory = client.app.state.session_factory
    with Session(engine) as db:
        job = db.scalar(select(AIJob))
        saved_name = job.payload["product"]["name"]
        assert db.scalar(select(AIRequestReservation)).id == job.reservation_id
    client.patch(
        f"/products/{product}", json={"name": "Changed product"}, headers=ORIGIN
    )
    job = jobs.claim(factory, settings)
    assert job
    asyncio.run(jobs.execute(factory, settings, model, job))
    result = client.get(f"/posts/{post['id']}/variants/{variant['id']}").json()
    assert result["status"] == "ready" and result["latest_revision"]["origin"] == "ai"
    assert saved_name in result["latest_revision"]["headline"]
    assert "Changed product" not in result["latest_revision"]["headline"]
    assert result["processing_metadata"]["source"] == "ai"
    assert result["processing_metadata"]["input_tokens"] == 100
    assert jobs.claim(factory, settings) is None
    assert len(calls) == 1


def test_unknown_provider_outcome_never_gets_reissued(client):
    client, engine = client
    _, post, settings, model, calls = prepare(client)
    variant = create(client, post)
    factory = client.app.state.session_factory
    claimed = jobs.claim(factory, settings)
    with Session(engine) as db:
        job = db.get(AIJob, claimed[0])
        job.lease_until = jobs.now() - timedelta(seconds=1)
        db.commit()
    assert jobs.claim(factory, settings) is None
    assert not calls
    result = client.get(f"/posts/{post['id']}/variants/{variant['id']}").json()
    assert result["status"] == "failed"
    assert result["processing_metadata"]["failure_code"] == "interrupted"
    assert jobs.claim(factory, settings) is None


def test_seller_revision_wins_over_late_ai_completion(client):
    client, _ = client
    _, post, settings, model, _ = prepare(client)
    variant = create(client, post)
    factory = client.app.state.session_factory
    claimed = jobs.claim(factory, settings)
    path = f"/posts/{post['id']}/variants/{variant['id']}"
    revised = client.post(path + "/revisions", json=CONTENT, headers=ORIGIN)
    assert revised.status_code == 201
    asyncio.run(jobs.execute(factory, settings, model, claimed))
    saved = client.get(path).json()
    assert saved["latest_revision"]["origin"] == "seller"
    assert saved["latest_revision"]["body"] == CONTENT["body"]
    assert len(client.get(path + "/revisions").json()) == 1


def test_fallback_revision_is_labeled_and_stale_worker_cannot_accept(client):
    client, engine = client
    _, post, settings, model, _ = prepare(
        client, {"hook_id": 0, "fact_ids": ["invented_claim"]}
    )
    variant = create(client, post)
    factory = client.app.state.session_factory
    asyncio.run(jobs.execute(factory, settings, model, jobs.claim(factory, settings)))
    result = client.get(f"/posts/{post['id']}/variants/{variant['id']}").json()
    assert result["latest_revision"]["origin"] == "fallback"
    assert result["processing_metadata"]["source"] == "fallback"
    assert result["processing_metadata"]["input_tokens"] == 100
    with Session(engine) as db:
        db.get(AIWorkerHeartbeat, "worker-test").updated_at = jobs.now() - timedelta(
            minutes=1
        )
        db.commit()
    rejected = client.post(
        f"/posts/{post['id']}/variants",
        json={
            "source_version_id": post["latest_version"]["id"],
            "platform": "instagram",
        },
        headers=ORIGIN,
    )
    assert rejected.status_code == 503
    with Session(engine) as db:
        assert len(db.scalars(select(AIJob)).all()) == 1


def test_expired_lease_cannot_persist_result(client):
    client, engine = client
    _, post, settings, model, _ = prepare(client)
    variant = create(client, post)
    factory = client.app.state.session_factory
    claimed = jobs.claim(factory, settings)
    result = GroundedPlatformGenerator(settings, model).generate(
        PlatformGenerationInput.model_validate(claimed[3])
    )
    with Session(engine) as db:
        db.get(AIJob, claimed[0]).lease_until = jobs.now() - timedelta(seconds=1)
        db.commit()
    jobs.finalize(factory, claimed[0], claimed[1], result, None, result.metadata)
    with Session(engine) as db:
        assert db.get(PlatformVariant, variant["id"]).status == "processing"


def test_image_dispatch_uses_private_snapshot_and_exposes_only_findings(
    setup, monkeypatch
):
    from test_product_images import login, make_product

    from app.services.ai.image import VisionImageAnalyzer
    from app.services.processing_admission import get_processing_admission

    client, engine, storage = setup
    client.app.dependency_overrides.pop(get_processing_admission)
    login(client, "image-jobs@example.com")
    product = make_product(client)
    image = client.post(
        f"/products/{product}/images",
        files={"file": ("example.png", image_bytes(), "image/png")},
        headers=ORIGIN,
    ).json()["id"]
    settings = client.app.state.settings
    settings.phase2_ai_enabled = True
    model, calls = gateway(settings, image_result())
    factory = client.app.state.session_factory
    jobs.publish_heartbeat(factory, "vision-test", settings, ["image_analysis"])
    path = f"/products/{product}/images/{image}/analyses"
    accepted = client.post(path, json={}, headers=ORIGIN)
    assert accepted.status_code == 202
    with Session(engine) as db:
        payload = db.scalar(select(AIJob)).payload
        assert payload["storage_key"] in storage.objects
        assert "image_url" not in payload
    monkeypatch.setattr(
        VisionImageAnalyzer, "load_private_image", lambda self, url: image_bytes()
    )

    def runner(settings, gateway, kind, payload):
        return jobs.perform(settings, gateway, kind, payload, storage=storage)

    asyncio.run(
        jobs.execute(
            factory, settings, model, jobs.claim(factory, settings), runner=runner
        )
    )
    response = client.get(path + f"/{accepted.json()['id']}").json()
    assert response["status"] == "completed"
    assert response["analysis_result"]["clarity"]["observation"]
    assert response["processing_metadata"]["input_tokens"] == 1200
    assert payload["storage_key"] not in str(response)
    assert not any("storage.example" in request.content.decode() for request in calls)
