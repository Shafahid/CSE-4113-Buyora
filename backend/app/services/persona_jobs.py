"""Durable variant generation: repeated starts reuse results, leases avoid rebilling."""

import asyncio
import json
from datetime import timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import or_, select

from app.core.persona_diversity import duplicate_perspectives
from app.models import PersonaAdaptation, Product, User
from app.schemas.execution import PERSONA_VERSION, PersonaAdaptResponse, PersonaProfile
from app.services.llm import ModelFailure, model_identity
from app.services.persona_engine import contextual_profiles, generate_variants
from app.services.simulation_runs import digest, now, prepare_inputs


def owned_adaptation(db, job_id, seller_id):
    job = db.scalar(
        select(PersonaAdaptation)
        .join(Product)
        .where(
            PersonaAdaptation.id == job_id,
            PersonaAdaptation.seller_id == seller_id,
            Product.deleted_at.is_(None),
        )
    )
    if not job:
        raise HTTPException(404, "Persona adaptation not found")
    return job


def adaptation_response(job, cache_hit=False):
    return PersonaAdaptResponse(
        id=job.id,
        status=job.status,
        profiles=job.result or [],
        source="fallback" if job.status == "fallback" else "ai",
        cache_hit=cache_hit,
        error_code=job.error_code,
    )


def start_adaptation(db, seller_id, data, settings):
    _, inputs, _ = prepare_inputs(db, seller_id, data, settings)
    inputs["persona_version"] = PERSONA_VERSION
    if data.mode == "context":
        return PersonaAdaptResponse(
            id=str(data.request_id),
            status="completed",
            profiles=contextual_profiles(inputs),
            source="context",
        )
    fingerprint = digest(inputs)
    db.scalar(select(User).where(User.id == seller_id).with_for_update())
    existing = db.scalar(
        select(PersonaAdaptation).where(
            PersonaAdaptation.seller_id == seller_id,
            PersonaAdaptation.request_id == str(data.request_id),
        )
    )
    if existing:
        if existing.fingerprint != fingerprint:
            raise HTTPException(409, "This request ID belongs to different inputs")
        return adaptation_response(existing, True)
    if not data.fresh:
        cached = db.scalar(
            select(PersonaAdaptation)
            .where(
                PersonaAdaptation.seller_id == seller_id,
                PersonaAdaptation.fingerprint == fingerprint,
            )
            .order_by(PersonaAdaptation.created_at.desc())
            .limit(1)
        )
        if cached:
            return adaptation_response(cached, True)
    job = PersonaAdaptation(
        id=str(uuid4()),
        seller_id=seller_id,
        product_id=inputs["product_id"],
        request_id=str(data.request_id),
        fingerprint=fingerprint,
        status="queued",
        inputs=inputs,
        usage={},
        created_at=now(),
    )
    db.add(job)
    db.commit()
    return adaptation_response(job)


def claim_adaptation(factory):
    with factory() as db:
        job = db.scalar(
            select(PersonaAdaptation)
            .where(
                or_(
                    PersonaAdaptation.status == "queued",
                    (PersonaAdaptation.status == "running")
                    & (PersonaAdaptation.lease_until < now()),
                )
            )
            .order_by(PersonaAdaptation.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not job:
            return None
        if job.status == "running":
            job.result = contextual_profiles(job.inputs)
            job.status = "fallback"
            job.error_code = "interrupted"
            job.lease_token = None
            job.lease_until = None
            db.commit()
            return None
        token = str(uuid4())
        job.status = "running"
        job.lease_token = token
        job.lease_until = now() + timedelta(seconds=90)
        inputs = job.inputs
        db.commit()
        return job.id, token, inputs


def finish_adaptation(factory, job_id, token, result, usage, error):
    with factory() as db:
        job = db.scalar(
            select(PersonaAdaptation)
            .where(
                PersonaAdaptation.id == job_id,
                PersonaAdaptation.lease_token == token,
                PersonaAdaptation.status == "running",
                PersonaAdaptation.lease_until > now(),
            )
            .with_for_update()
        )
        if not job:
            return
        job.result, job.usage, job.error_code = result, usage, error
        job.status = "fallback" if error else "completed"
        job.lease_until = None
        job.lease_token = None
        db.commit()


async def execute_adaptation(factory, settings, job_id, token, inputs, evaluator=None):
    async def heartbeat():
        while True:
            await asyncio.sleep(10)

            def renew():
                with factory() as db:
                    job = db.scalar(
                        select(PersonaAdaptation)
                        .where(
                            PersonaAdaptation.id == job_id,
                            PersonaAdaptation.lease_token == token,
                            PersonaAdaptation.lease_until > now(),
                        )
                        .with_for_update()
                    )
                    if job:
                        job.lease_until = now() + timedelta(seconds=90)
                        db.commit()

            await asyncio.to_thread(renew)

    task = asyncio.create_task(heartbeat())
    usage, error = {}, None
    try:
        if inputs.get("persona_version") != PERSONA_VERSION:
            raise ModelFailure("configuration_changed")
        if inputs.get("model_config") != {
            "model": model_identity(settings),
            "endpoint": settings.token_bd_api_url,
            "json_mode": settings.llm_json_mode,
        }:
            raise ModelFailure("configuration_changed")
        reserve = (
            len(json.dumps(inputs, ensure_ascii=False).encode()) // 3
            + settings.llm_max_output_tokens
            + 512
        )
        if reserve > settings.simulation_token_budget:
            raise ModelFailure("token_budget")
        result, usage = await asyncio.wait_for(
            (evaluator or generate_variants)(settings, inputs),
            timeout=settings.llm_timeout_seconds + 5,
        )
        result = [
            PersonaProfile.model_validate(profile).model_dump() for profile in result
        ]
        if (
            len(result) != len(inputs["personas"])
            or {profile["id"] for profile in result}
            != {profile["id"] for profile in inputs["personas"]}
            or duplicate_perspectives(result)
        ):
            raise ValueError("Generated profiles must preserve distinct identities")
    except ModelFailure as exc:
        result, error, usage = contextual_profiles(inputs), exc.code, exc.metadata
    except (TimeoutError, ValueError):
        result, error = contextual_profiles(inputs), "invalid_or_timed_out"
    except Exception:
        result, error = contextual_profiles(inputs), "generation_failed"
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    await asyncio.to_thread(
        finish_adaptation, factory, job_id, token, result, usage, error
    )
