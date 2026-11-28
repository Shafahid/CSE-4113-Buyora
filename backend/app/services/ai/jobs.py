"""Transactional optional-AI queue. Unknown in-flight calls are never replayed."""

import asyncio
import contextlib
import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import or_, select

from app.models import (
    AIJob,
    AIRequestReservation,
    AIWorkerHeartbeat,
    MarketAnalysis,
    PlatformVariant,
    PlatformVariantRevision,
    Post,
    PostVersion,
    Product,
    ProductImageAnalysis,
)
from app.schemas.phase2 import ExecutionBudget
from app.services.ai.image import VisionImageAnalyzer
from app.services.ai.market import GroundedMarketAnalyzer, verify_grounding
from app.services.ai.platform import GroundedPlatformGenerator
from app.services.ai.provider import (
    PROMPT_VERSION,
    Gateway,
    configured,
    failure_usage,
    metadata,
)
from app.services.image_analysis import ImageAnalysisInput
from app.services.llm import ModelFailure
from app.services.market_analysis import MarketInput
from app.services.platform_content import PlatformGenerationInput
from app.services.processing_admission import DurableProcessingAdmission

logger = logging.getLogger(__name__)
LEASE_SECONDS = 90
MODELS = {
    "image_analysis": ProductImageAnalysis,
    "market_analysis": MarketAnalysis,
    "platform_generation": PlatformVariant,
}


def now():
    return datetime.now(UTC)


def configuration(settings):
    values = [
        settings.token_bd_api_url,
        settings.token_bd_model,
        settings.token_bd_vision_model,
        settings.llm_json_mode,
        settings.llm_fallback_enabled,
        settings.market_evidence_max_age_days,
        PROMPT_VERSION,
    ]
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()


def product_snapshot(product):
    return {
        key: (str(product.price) if key == "price" else getattr(product, key))
        for key in (
            "name",
            "category",
            "description",
            "features",
            "price",
            "currency",
            "delivery_info",
            "return_policy",
            "warranty",
        )
    }


def active_resource(db, kind, resource_id):
    if kind == "platform_generation":
        return db.scalar(
            select(PlatformVariant)
            .join(PostVersion, PostVersion.id == PlatformVariant.source_version_id)
            .join(Post, Post.id == PostVersion.post_id)
            .join(Product, Product.id == Post.product_id)
            .where(PlatformVariant.id == resource_id, Product.deleted_at.is_(None))
            .with_for_update(of=PlatformVariant)
        )
    model = MODELS[kind]
    return db.scalar(
        select(model)
        .join(Product, Product.id == model.product_id)
        .where(
            model.id == resource_id,
            Product.seller_id == model.seller_id,
            Product.deleted_at.is_(None),
        )
        .with_for_update(of=model)
    )


class DatabaseAdmission(DurableProcessingAdmission):
    def __init__(self, settings):
        self.settings = settings

    def verify_ready(self, db, kind):
        if not self.settings.phase2_ai_enabled or kind not in MODELS:
            raise ModelFailure("processor_unavailable")
        workers = db.scalars(
            select(AIWorkerHeartbeat)
            .where(
                AIWorkerHeartbeat.updated_at > now() - timedelta(seconds=30),
                AIWorkerHeartbeat.configuration == configuration(self.settings),
            )
            .limit(100)
        ).all()
        if not any(kind in worker.capabilities for worker in workers):
            raise ModelFailure("processor_unavailable")

    def enqueue(self, db, kind, resource_id):
        self.verify_ready(db, kind)
        reservation = db.scalar(
            select(AIRequestReservation).where(
                AIRequestReservation.kind == kind,
                AIRequestReservation.resource_id == resource_id,
            )
        )
        if not reservation:
            raise ModelFailure("missing_reservation")
        resource = active_resource(db, kind, resource_id)
        if resource is None or resource.status != "pending":
            raise ModelFailure("resource_unavailable")
        budget = ExecutionBudget.model_validate(reservation.policy).model_dump()
        if kind == "image_analysis":
            product = db.get(Product, resource.product_id)
            if (
                product.seller_id != reservation.seller_id
                or not resource.snapshot_storage_key
            ):
                raise ModelFailure("resource_unavailable")
            payload = {
                "product_id": resource.product_id,
                "image_id": resource.original_image_id,
                "product_details": product_snapshot(product),
                "language": resource.language,
                "storage_key": resource.snapshot_storage_key,
                "budget": budget,
            }
        elif kind == "market_analysis":
            if resource.seller_id != reservation.seller_id:
                raise ModelFailure("resource_unavailable")
            payload = {**resource.input_snapshot, "budget": budget}
        else:
            version = db.get(PostVersion, resource.source_version_id)
            post = db.get(Post, version.post_id)
            product = db.get(Product, post.product_id)
            if product.seller_id != reservation.seller_id:
                raise ModelFailure("resource_unavailable")
            payload = {
                "source_version_id": version.id,
                "platform": resource.platform,
                "language": resource.language,
                "preferences": resource.preferences,
                "post": {
                    key: getattr(version, key)
                    for key in (
                        "headline",
                        "body",
                        "offer",
                        "call_to_action",
                        "hashtags",
                        "platform",
                    )
                },
                "product": product_snapshot(product),
                "budget": budget,
            }
        db.add(
            AIJob(
                id=str(uuid4()),
                reservation_id=reservation.id,
                seller_id=reservation.seller_id,
                kind=kind,
                resource_id=resource_id,
                status="queued",
                payload=payload,
                configuration=configuration(self.settings),
                created_at=now(),
                updated_at=now(),
            )
        )
        db.flush()


def publish_heartbeat(factory, worker_id, settings, capabilities):
    with factory() as db:
        row = db.get(AIWorkerHeartbeat, worker_id)
        if row is None:
            row = AIWorkerHeartbeat(id=worker_id)
            db.add(row)
        row.updated_at = now()
        row.capabilities = capabilities
        row.configuration = configuration(settings)
        db.commit()


def finish_locked(db, job, resource, result=None, error=None, provenance=None):
    finished = now()
    provenance = provenance or metadata(
        "unavailable", None, PROMPT_VERSION, failure_code=error
    )
    payload = provenance.model_dump(mode="json")
    if resource is not None and resource.status == "processing":
        resource.updated_at = finished
        resource.processing_metadata = payload
        resource.error_message = (
            None if error is None else f"AI processing unavailable ({error})."
        )
        resource.status = (
            "failed"
            if error
            else "ready"
            if job.kind == "platform_generation"
            else "completed"
        )
        if job.kind == "platform_generation":
            if result:
                # Preserve seller revisions if they were saved while the AI call ran.
                latest = (
                    db.scalar(
                        select(PlatformVariantRevision.revision_number)
                        .where(PlatformVariantRevision.variant_id == resource.id)
                        .order_by(PlatformVariantRevision.revision_number.desc())
                        .limit(1)
                    )
                    or 0
                )
                db.add(
                    PlatformVariantRevision(
                        variant_id=resource.id,
                        revision_number=latest + 1,
                        origin="fallback" if provenance.source == "fallback" else "ai",
                        **result.content.model_dump(),
                    )
                )
        else:
            resource.completed_at = finished
            if result:
                resource.analysis_result = result.model_dump(mode="json")
    job.status = "failed" if error else "completed"
    job.updated_at = job.completed_at = finished
    job.lease_token = job.lease_until = None
    job.error_code, job.usage = error, payload


def claim(factory, settings):
    with factory() as db:
        job = db.scalar(
            select(AIJob)
            .where(
                or_(
                    AIJob.status == "queued",
                    (AIJob.status == "running") & (AIJob.lease_until < now()),
                )
            )
            .order_by(AIJob.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not job:
            return None
        resource = active_resource(db, job.kind, job.resource_id)
        if job.status == "running":
            finish_locked(db, job, resource, error="interrupted")
            db.commit()
            return None
        if resource is None or resource.status != "pending":
            finish_locked(db, job, resource, error="resource_superseded")
            db.commit()
            return None
        if job.configuration != configuration(settings):
            resource.status = "processing"
            finish_locked(db, job, resource, error="configuration_changed")
            db.commit()
            return None
        token = str(uuid4())
        job.status, job.lease_token = "running", token
        job.lease_until = now() + timedelta(seconds=LEASE_SECONDS)
        job.updated_at = now()
        resource.status = "processing"
        resource.updated_at = now()
        db.commit()
        return job.id, token, job.kind, dict(job.payload)


def renew(factory, job_id, token):
    with factory() as db:
        job = db.scalar(
            select(AIJob)
            .where(
                AIJob.id == job_id,
                AIJob.status == "running",
                AIJob.lease_token == token,
                AIJob.lease_until > now(),
            )
            .with_for_update()
        )
        if job:
            job.lease_until = now() + timedelta(seconds=LEASE_SECONDS)
            job.updated_at = now()
            db.commit()
            return True
        return False


def finalize(factory, job_id, token, result, error, provenance):
    with factory() as db:
        job = db.scalar(
            select(AIJob)
            .where(
                AIJob.id == job_id,
                AIJob.status == "running",
                AIJob.lease_token == token,
                AIJob.lease_until > now(),
            )
            .with_for_update()
        )
        if not job:
            return
        resource = active_resource(db, job.kind, job.resource_id)
        if resource is None or resource.status != "processing":
            finish_locked(
                db, job, None, error="resource_superseded", provenance=provenance
            )
        else:
            finish_locked(db, job, resource, result, error, provenance)
        db.commit()


def perform(settings, gateway, kind, payload, storage=None):
    if kind == "image_analysis":
        from app.core.storage import StorageClient

        storage = storage or StorageClient(settings)
        data = {key: value for key, value in payload.items() if key != "storage_key"}
        data["image_url"] = storage.signed_url(payload["storage_key"])
        return VisionImageAnalyzer(settings, gateway).analyze(
            ImageAnalysisInput(**data)
        )
    if kind == "market_analysis":
        data = MarketInput.model_validate(payload)
        result = GroundedMarketAnalyzer(settings, gateway).analyze(data)
        if not verify_grounding(data, result, settings):
            raise ModelFailure("ungrounded_output")
        return result
    return GroundedPlatformGenerator(settings, gateway).generate(
        PlatformGenerationInput.model_validate(payload)
    )


async def execute(factory, settings, gateway, job, *, runner=None):
    job_id, token, kind, payload = job

    async def keep_lease():
        while True:
            await asyncio.sleep(5)
            if not await asyncio.to_thread(renew, factory, job_id, token):
                return

    task = asyncio.create_task(keep_lease())
    result, error, provenance = None, None, None
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(runner or perform, settings, gateway, kind, payload),
            timeout=payload["budget"]["timeout_seconds"] + 20,
        )
        provenance = result.metadata
        if provenance is None:
            raise ModelFailure("missing_provenance")
    except ModelFailure as failure:
        error = failure.code
        provenance = metadata(
            "unavailable",
            gateway.model(vision=kind == "image_analysis"),
            PROMPT_VERSION,
            failure_code=error,
            **failure_usage(failure),
        )
    except TimeoutError:
        error = "provider_timeout"
    except Exception:
        error = "processing_failed"
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    await asyncio.to_thread(finalize, factory, job_id, token, result, error, provenance)


async def worker_loop(factory, settings):
    worker_id = str(uuid4())
    gateway = Gateway(settings)
    capabilities = []
    stop = asyncio.Event()

    async def advertise():
        checked = 0
        while not stop.is_set():
            nonlocal capabilities
            if checked % 12 == 0:
                capabilities = (
                    ["market_analysis", "platform_generation"]
                    if configured(settings) or settings.llm_fallback_enabled
                    else []
                )
                if (
                    settings.supabase_url
                    and settings.supabase_secret_key
                    and settings.supabase_storage_bucket
                    and await asyncio.to_thread(gateway.vision_ready)
                ):
                    capabilities.append("image_analysis")
            await asyncio.to_thread(
                publish_heartbeat, factory, worker_id, settings, capabilities
            )
            checked += 1
            await asyncio.sleep(5)

    heartbeat = asyncio.create_task(advertise())
    delay, warned = 1, False
    try:
        while True:
            try:
                if heartbeat.done():
                    # A dead heartbeat must never leave a falsely healthy processor.
                    await heartbeat
                job = await asyncio.to_thread(claim, factory, settings)
                if job:
                    await execute(factory, settings, gateway, job)
                if warned:
                    logger.info("Optional AI queue recovered")
                delay, warned = 1, False
            except Exception as error:
                if not warned:
                    from app.services.simulation_worker import worker_failure_hint

                    logger.warning(
                        "Optional AI worker unavailable (%s). %s",
                        type(error).__name__,
                        worker_failure_hint(error),
                    )
                    warned = True
                delay = min(delay * 2, 30)
                if heartbeat.done():
                    heartbeat = asyncio.create_task(advertise())
            await asyncio.sleep(delay)
    finally:
        stop.set()
        heartbeat.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await heartbeat

        # Expire on shutdown; interrupted running jobs retain their lease until
        # recovery marks them failed, without dispatching another paid call.
        def remove_heartbeat():
            with factory() as db:
                row = db.get(AIWorkerHeartbeat, worker_id)
                if row:
                    db.delete(row)
                    db.commit()

        with contextlib.suppress(Exception):
            await asyncio.to_thread(remove_heartbeat)
