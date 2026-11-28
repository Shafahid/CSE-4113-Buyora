import hashlib
import json
import re
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import (
    PersonaEvaluation,
    Post,
    PostVersion,
    Product,
    Simulation,
    SimulationCache,
    SimulationPersona,
    SimulationRun,
    User,
)
from app.schemas.execution import (
    PROMPT_VERSION,
    RULES_VERSION,
    RunCreate,
    RunProgress,
    RunResponse,
)
from app.services.llm import model_identity
from app.services.report_insights import objection_groups, recommendations
from app.services.trust_scoring import trust_signals

TERMINAL = {"completed", "partially_failed", "failed"}


def now():
    return datetime.now(UTC)


def utc_time(value):
    # SQLite drops timezone information; persisted execution times are UTC.
    return value.replace(tzinfo=UTC) if value and value.tzinfo is None else value


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def owned_run(db: Session, run_id: str, user_id: int, *, lock=False):
    query = (
        select(SimulationRun)
        .join(Simulation, Simulation.id == SimulationRun.simulation_id)
        .join(PostVersion, PostVersion.id == Simulation.post_version_id)
        .join(Post, Post.id == PostVersion.post_id)
        .join(Product, Product.id == Post.product_id)
        .where(
            SimulationRun.id == run_id,
            SimulationRun.seller_id == user_id,
            Product.deleted_at.is_(None),
        )
    )
    if lock:
        query = query.with_for_update(of=SimulationRun)
    run = db.scalar(query)
    if not run:
        raise HTTPException(404, "Simulation run not found")
    return run


def evaluations(db, run_id):
    return list(
        db.scalars(
            select(PersonaEvaluation)
            .where(PersonaEvaluation.run_id == run_id)
            .order_by(PersonaEvaluation.id)
        )
    )


def can_retry(row):
    if (row.output or {}).get("evaluation_source") == "fallback":
        return row.attempts < 6 and row.error_code != "configuration_changed"
    return (
        (
            row.status == "failed"
            or (row.output or {}).get("evaluation_source") == "fallback"
        )
        and row.attempts < 6
        and row.error_code
        not in {
            "provider_auth",
            "provider_configuration",
            "configuration_changed",
            "output_truncated",
        }
    )


def response(db, run, cache_hit=False, *, include_report=True):
    rows = evaluations(db, run.id)
    return (RunResponse if include_report else RunProgress)(
        id=run.id,
        simulation_id=run.simulation_id,
        status=run.status,
        total=len(rows),
        completed=sum(e.status == "completed" for e in rows),
        failed=sum(e.status == "failed" for e in rows),
        cache_hit=cache_hit,
        model=run.model,
        created_at=utc_time(run.created_at),
        started_at=utc_time(run.started_at),
        updated_at=utc_time(run.updated_at),
        evaluations=[
            {
                "id": e.id,
                "profile": e.profile,
                "status": e.status,
                "attempts": e.attempts,
                "error_code": e.error_code,
                "output": e.output,
                "can_retry": can_retry(e),
            }
            for e in rows
        ],
        **({"report": run.report} if include_report else {}),
    )


def audience_settings(audience):
    """Persist the structured draft shape used by the existing simulation API."""
    value = {}
    mapping = {"location": "location", "needs": "product_needs"}
    for source, target in mapping.items():
        if audience.get(source):
            value[target] = audience[source]
    ages = re.findall(r"\d+", audience.get("age", ""))
    if ages:
        value["age_range"] = {"min": int(ages[0])}
        if len(ages) > 1:
            value["age_range"]["max"] = int(ages[1])
    if audience.get("interests"):
        value["interests"] = [
            s.strip() for s in audience["interests"].split(",") if s.strip()
        ]
    budget = audience.get("budget", "").split(" ")[0].lower()
    if budget in {"low", "medium", "high"}:
        value["budget_sensitivity"] = budget
    preference = {
        "Cash on delivery": "cash_on_delivery",
        "Online payment": "online_payment",
        "In-store pickup": "in_store_pickup",
    }.get(audience.get("preferences"))
    if preference:
        value["purchasing_preference"] = preference
    return value


def prepare_inputs(
    db: Session, user_id: int, data: RunCreate, settings: Settings, *, lock=False
):
    if len(data.personas) > settings.simulation_max_personas:
        raise HTTPException(422, "Too many personas for this simulation")
    query = (
        select(PostVersion)
        .join(Post, Post.id == PostVersion.post_id)
        .join(Product, Product.id == Post.product_id)
        .where(
            PostVersion.id == data.post_version_id,
            Product.seller_id == user_id,
            Product.deleted_at.is_(None),
            Product.status == "active",
        )
    )
    version = db.scalar(query.with_for_update(of=Post) if lock else query)
    if not version:
        raise HTTPException(404, "Active product post version not found")
    post = db.get(Post, version.post_id)
    product = db.get(Product, post.product_id)
    product_input = {
        key: getattr(product, key)
        for key in (
            "name",
            "category",
            "description",
            "features",
            "warranty",
            "delivery_info",
            "return_policy",
            "currency",
        )
    }
    product_input["price"] = str(product.price)
    post_input = {
        key: getattr(version, key)
        for key in (
            "headline",
            "body",
            "offer",
            "call_to_action",
            "hashtags",
            "platform",
        )
    }
    profiles = [p.model_dump() for p in data.personas]
    audience = {
        key: data.audience.get(key, "")
        for key in ("location", "age", "interests", "preferences", "budget", "needs")
    }
    checks = {
        "price_supplied": True,
        "delivery_supplied": bool(product.delivery_info),
        "returns_supplied": bool(product.return_policy),
        "warranty_supplied": bool(product.warranty),
        "ordering_instructions_supplied": bool(version.call_to_action),
    }
    inputs = {
        "product_id": product.id,
        "post_id": post.id,
        "post_version_id": version.id,
        "version_number": version.version_number,
        "product": product_input,
        "post": post_input,
        "audience": audience,
        "language": data.language,
        "personas": profiles,
        "checks": checks,
        "rules_version": RULES_VERSION,
        "prompt_version": PROMPT_VERSION,
        "execution_policy": {
            "fallback_enabled": settings.llm_fallback_enabled,
            "max_model_calls": settings.simulation_max_model_calls,
            "token_budget": settings.simulation_token_budget,
        },
        "model_config": {
            "model": model_identity(settings),
            "endpoint": settings.token_bd_api_url,
            "json_mode": settings.llm_json_mode,
        },
    }
    # UI identity/colour and list order do not change a buyer's evaluation.
    semantic_profiles = sorted(
        [
            {k: v for k, v in p.items() if k not in {"id", "color", "initials"}}
            for p in profiles
        ],
        key=lambda p: json.dumps(p, sort_keys=True),
    )
    fingerprint = digest(
        {
            **inputs,
            "personas": semantic_profiles,
            "model": model_identity(settings),
            "endpoint": settings.token_bd_api_url,
            "json_mode": settings.llm_json_mode,
            "rules": RULES_VERSION,
        }
    )
    return version, inputs, fingerprint


def create_run(db: Session, user_id: int, data: RunCreate, settings: Settings):
    # Serialize cache lookup and publication for each seller.
    db.scalar(select(User).where(User.id == user_id).with_for_update())
    version, inputs, fingerprint = prepare_inputs(
        db, user_id, data, settings, lock=True
    )
    product_input = inputs["product"]
    audience = inputs["audience"]
    profiles = inputs["personas"]
    existing = db.scalar(
        select(SimulationRun).where(
            SimulationRun.seller_id == user_id,
            SimulationRun.request_id == str(data.request_id),
        )
    )
    if existing:
        if existing.fingerprint != fingerprint:
            raise HTTPException(409, "This request ID belongs to different inputs")
        return response(db, existing, True)
    cached = db.get(SimulationCache, (user_id, fingerprint))
    if cached and not data.fresh:
        run = db.get(SimulationRun, cached.run_id)
        return response(db, run, True)
    if not settings.llm_fallback_enabled and not (
        settings.token_bd_api_url
        and settings.token_bd_api_key
        and settings.token_bd_model
    ):
        raise HTTPException(503, "The simulation model is not configured")
    simulation = Simulation(
        post_version_id=version.id,
        audience_settings=audience_settings(audience),
        language=data.language,
        product_snapshot=product_input,
        evaluation_rules_version=RULES_VERSION,
        status="queued",
    )
    db.add(simulation)
    db.flush()
    run = SimulationRun(
        id=str(uuid4()),
        simulation_id=simulation.id,
        seller_id=user_id,
        request_id=str(data.request_id),
        fingerprint=fingerprint,
        status="queued",
        expected_personas=len(profiles),
        inputs=inputs,
        model=model_identity(settings),
        rules_version=RULES_VERSION,
        created_at=now(),
        updated_at=now(),
    )
    db.add(run)
    db.flush()
    for profile in profiles:
        sensitivity = profile["budget"].split(" ")[0].lower()
        persona = SimulationPersona(
            simulation_id=simulation.id,
            name=profile["name"],
            characteristics={
                "label": profile["role"],
                "age": profile["age"],
                "location": profile["location"],
                "client_id": profile["id"],
            },
            needs=[profile["need"]],
            preferences=[],
            budget_sensitivity=sensitivity
            if sensitivity in {"low", "medium", "high"}
            else None,
            is_selected=True,
        )
        db.add(persona)
        db.flush()
        db.add(
            PersonaEvaluation(
                run_id=run.id,
                persona_id=persona.id,
                profile=profile,
                status="queued",
                attempts=0,
                history=[],
                updated_at=now(),
            )
        )
    if cached:
        cached.run_id = run.id
    else:
        db.add(
            SimulationCache(seller_id=user_id, fingerprint=fingerprint, run_id=run.id)
        )
    db.commit()
    return response(db, run)


def build_report(run, rows):
    """Freeze the existing screen contract. Scores are aggregated in code."""
    source = run.inputs
    product = source["product"]
    post = source["post"]
    reactions = []
    for row in rows:
        verdict = row.output or {}
        scores = verdict.get("scores", [0] * 7)
        score = int(sum(scores) / 7 + 0.5)
        reactions.append(
            {
                "persona": row.profile,
                "evaluationId": row.id,
                "status": "complete" if row.status == "completed" else "failed",
                "scores": scores,
                "score": score,
                "sentiment": "Interested"
                if score >= 76
                else "Has questions"
                if score >= 60
                else "Unconvinced",
                **{
                    key: verdict.get(key, "")
                    for key in ("comment", "reason", "positive", "question")
                },
                "evidence": verdict.get("evidence", []),
                "errorCode": row.error_code,
                "evaluationSource": verdict.get("evaluation_source", "ai"),
                "fallbackReason": verdict.get("fallback_reason"),
                "objections": verdict.get("objections", []),
                "scoreDrivers": verdict.get("score_drivers", []),
            }
        )
    return {
        "id": run.id,
        "source": "server",
        "model": run.model,
        "rulesVersion": run.rules_version,
        "promptVersion": source.get("prompt_version"),
        "trustSignals": trust_signals(source),
        "recommendations": recommendations(source, rows),
        "objectionGroups": objection_groups(rows),
        "fallbackCount": sum(
            (row.output or {}).get("evaluation_source") == "fallback" for row in rows
        ),
        "usage": {
            "modelCalls": sum(row.attempts for row in rows),
            "inputTokens": sum(
                event.get("input_tokens") or 0 for row in rows for event in row.history
            ),
            "outputTokens": sum(
                event.get("output_tokens") or 0 for row in rows for event in row.history
            ),
            "latencyMs": sum(
                event.get("latency_ms") or 0 for row in rows for event in row.history
            ),
        },
        "title": product["name"],
        "createdAt": utc_time(run.created_at).isoformat(),
        "product": {
            "id": str(source["product_id"]),
            "name": product["name"],
            "price": float(product["price"]),
            "category": product["category"],
            "description": product["description"] or "",
            "features": "\n".join(product["features"] or []),
            "warranty": product["warranty"] or "",
            "delivery": product["delivery_info"] or "",
            "returns": product["return_policy"] or "",
            "image": "",
            "art": "tote",
            "archived": False,
        },
        "post": {
            "id": str(source["post_id"]),
            "productId": str(source["product_id"]),
            "headline": post["headline"],
            "body": post["body"],
            "offer": post["offer"] or "",
            "cta": post["call_to_action"] or "",
            "hashtags": " ".join(post["hashtags"] or []),
            "platform": post["platform"],
            "versions": [],
            "latestVersionId": str(source["post_version_id"]),
            "versionNumber": source["version_number"],
        },
        "audience": source["audience"],
        "language": source["language"],
        "reactions": reactions,
        "revised": "",
        "applied": [],
        "checks": source["checks"],
        "coverage": {
            "completed": sum(row.status == "completed" for row in rows),
            "total": len(rows),
            "failed": sum(row.status == "failed" for row in rows),
        },
    }
