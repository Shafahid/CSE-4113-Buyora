"""Database queue + bounded LangGraph persona workers.

Successful persona results survive restarts. An interrupted in-flight provider call
is marked failed for explicit retry: its remote completion cannot be known safely.
"""

import asyncio
import contextlib
import logging
from datetime import timedelta
from typing import TypedDict
from uuid import uuid4

from sqlalchemy import or_, select

from app.models import PersonaEvaluation, Simulation, SimulationRun
from app.schemas.execution import RULES_VERSION, Verdict
from app.services.llm import (
    ModelFailure,
    evaluate_persona,
    model_identity,
    persona_token_reservation,
)
from app.services.simulation_runs import build_report, evaluations, now
from app.services.trust_scoring import deterministic_evaluation, evaluation_metadata

logger = logging.getLogger(__name__)
LEASE_SECONDS = 90


def worker_failure_hint(error):
    """Classify failures without logging driver messages or connection secrets."""
    original = getattr(error, "orig", error)
    state = getattr(original, "sqlstate", None)
    if state in {"42P01", "42703"}:
        return "Database schema is outdated; run uv run alembic upgrade head"
    if state in {"28P01", "28000"}:
        return "Database authentication failed; check DATABASE_URL credentials"
    if state == "53300":
        return "Database connection limit reached; check pooler capacity"
    message = str(original).lower()
    if any(term in message for term in ("getaddrinfo", "could not translate host")):
        return "Database hostname could not be resolved; check DNS and DATABASE_URL"
    if "timeout" in message or "timed out" in message:
        return "Database connection timed out; check network and pooler availability"
    return "Check database connectivity and migrations"


def claim(factory):
    with factory() as db:
        run = db.scalar(
            select(SimulationRun)
            .where(
                or_(
                    SimulationRun.status == "queued",
                    (SimulationRun.status == "running")
                    & (SimulationRun.lease_until < now()),
                )
            )
            .order_by(SimulationRun.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not run:
            return None
        # Unknown in-flight outcomes must not silently spend another API call.
        for row in evaluations(db, run.id):
            if row.status == "running":
                row.status = "failed"
                row.error_code = "interrupted"
                row.updated_at = now()
                row.history = [
                    *row.history,
                    {"at": now().isoformat(), "error": "interrupted"},
                ]
        token = str(uuid4())
        run.status = "running"
        run.stage = "evaluating"
        run.started_at = run.started_at or now()
        run.updated_at = now()
        run.lease_token = token
        run.lease_until = now() + timedelta(seconds=LEASE_SECONDS)
        simulation = db.get(Simulation, run.simulation_id)
        simulation.status = "running"
        simulation.started_at = run.started_at
        db.commit()
        return run.id, token


def leased_run(db, run_id, token):
    run = db.scalar(
        select(SimulationRun)
        .where(
            SimulationRun.id == run_id,
            SimulationRun.lease_token == token,
            SimulationRun.status == "running",
            SimulationRun.lease_until > now(),
        )
        .with_for_update()
    )
    return run


def heartbeat(factory, run_id, token):
    with factory() as db:
        run = leased_run(db, run_id, token)
        if not run:
            return False
        run.lease_until = now() + timedelta(seconds=LEASE_SECONDS)
        run.updated_at = now()
        db.commit()
        return True


def accounted_tokens(rows):
    """Charge known usage once per attempt, reserving unknown/in-flight usage."""
    total = 0
    for row in rows:
        reservations = {}
        reported = {}
        for event in row.history:
            attempt = event.get("attempt", 0)
            reservations[attempt] = max(
                reservations.get(attempt, 0), event.get("reserved_tokens", 0)
            )
            usage = [event.get("input_tokens"), event.get("output_tokens")]
            if all(type(value) is int and value >= 0 for value in usage):
                reported[attempt] = max(reported.get(attempt, 0), sum(usage))
            else:
                # A partial usage report cannot release an unknown allowance.
                reservations[attempt] = max(
                    reservations[attempt],
                    sum(value for value in usage if type(value) is int and value >= 0),
                )
        total += sum(
            reported.get(attempt, reserved)
            for attempt, reserved in reservations.items()
        )
    return total


def prepare_attempt(factory, run_id, token, evaluation_id, settings):
    with factory() as db:
        run = leased_run(db, run_id, token)
        if not run:
            return None
        row = db.get(PersonaEvaluation, evaluation_id)
        if not row or row.run_id != run_id or row.status in {"completed", "failed"}:
            return None
        rows = evaluations(db, run_id)
        policy = run.inputs.get("execution_policy", {})
        block = "retry_limit" if row.attempts >= 6 else None
        if sum(item.attempts for item in rows) >= min(
            policy.get("max_model_calls", 66), settings.simulation_max_model_calls
        ):
            block = "model_call_budget"
        # Reserve a conservative token allowance while holding the run lock, so
        # parallel dispatches cannot all spend the same remaining budget.
        spent = accounted_tokens(rows)
        reserve = persona_token_reservation(settings, run.inputs, row.profile)
        if spent + reserve > min(
            policy.get("token_budget", 200000), settings.simulation_token_budget
        ):
            block = "token_budget"
        if block:
            if not policy.get("fallback_enabled", False):
                row.status, row.error_code = "failed", block
                row.updated_at = now()
                db.commit()
                return None
            return run.inputs, row.profile, block
        row.status = "running"
        row.attempts += 1
        row.history = [
            *row.history,
            {
                "event": "attempt_started",
                "attempt": row.attempts,
                "reserved_tokens": reserve,
                "at": now().isoformat(),
            },
        ]
        row.error_code = None
        row.updated_at = now()
        run.updated_at = now()
        db.commit()
        return run.inputs, row.profile, None


def save_attempt(factory, run_id, token, evaluation_id, output, metadata, error, retry):
    with factory() as db:
        run = leased_run(db, run_id, token)
        if not run:
            return
        row = db.get(PersonaEvaluation, evaluation_id)
        if not row:
            return
        row.output = output
        row.status = "completed" if output else "queued" if retry else "failed"
        row.error_code = error
        row.updated_at = now()
        row.history = [
            *row.history,
            {
                "attempt": row.attempts,
                "at": now().isoformat(),
                "error": error,
                **metadata,
            },
        ]
        run.updated_at = now()
        db.commit()


def work_ids(factory, run_id, token):
    with factory() as db:
        run = leased_run(db, run_id, token)
        if not run:
            return []
        return [row.id for row in evaluations(db, run_id) if row.status == "queued"]


def finalize(factory, run_id, token):
    with factory() as db:
        run = leased_run(db, run_id, token)
        if not run:
            return
        rows = evaluations(db, run_id)
        if any(row.status not in {"completed", "failed"} for row in rows):
            return
        complete = sum(row.status == "completed" for row in rows)
        run.status = (
            "completed"
            if complete == len(rows)
            else ("partially_failed" if complete else "failed")
        )
        run.completed_at = now()
        run.stage = {
            "completed": "report_ready",
            "partially_failed": "report_ready_partial",
            "failed": "failed",
        }[run.status]
        run.updated_at = now()
        run.lease_until = None
        run.lease_token = None
        previous = run.report or {}
        run.report = {
            **build_report(run, rows),
            "revised": previous.get("revised", ""),
            "applied": previous.get("applied", []),
        }
        simulation = db.get(Simulation, run.simulation_id)
        simulation.status = run.status
        simulation.completed_at = run.completed_at
        simulation.analysis = {
            "run_id": run.id,
            "completed": complete,
            "total": len(rows),
            "rules_version": run.rules_version,
            "fallback_count": run.report["fallbackCount"],
            "usage": run.report["usage"],
        }
        db.commit()


async def execute_run(factory, settings, run_id, token, evaluator=None):
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import Send

    class State(TypedDict):
        ids: list[int]

    class PersonaTask(TypedDict):
        evaluation_id: int

    async def persona_node(state: PersonaTask):
        evaluation_id = state["evaluation_id"]
        retry_feedback = None
        for attempt in range(settings.llm_max_attempts):
            prepared = await asyncio.to_thread(
                prepare_attempt, factory, run_id, token, evaluation_id, settings
            )
            if not prepared:
                return {}
            inputs, profile, blocked = prepared
            output = None
            metadata = {}
            error = None
            retry = False
            try:
                # Do not run a queued snapshot under a silently changed model.
                if blocked:
                    raise ModelFailure(blocked)
                if inputs.get("rules_version") != RULES_VERSION:
                    raise ModelFailure("configuration_changed")
                expected = inputs.get("model_config", {})
                if expected != {
                    "model": model_identity(settings),
                    "endpoint": settings.token_bd_api_url,
                    "json_mode": settings.llm_json_mode,
                }:
                    raise ModelFailure("configuration_changed")
                call = (
                    evaluator(settings, inputs, profile)
                    if evaluator is not None
                    else evaluate_persona(
                        settings, inputs, profile, retry_feedback=retry_feedback
                    )
                )
                output, metadata = await asyncio.wait_for(
                    call,
                    timeout=settings.llm_timeout_seconds + 5,
                )
                output = Verdict.model_validate(
                    {**output, **evaluation_metadata()}
                ).model_dump()
                metadata = {**metadata, **evaluation_metadata()}
            except ModelFailure as exc:
                output = None
                error = exc.code
                metadata = exc.metadata
                retry_feedback = metadata.get("validation_check")
                retry = exc.retryable and attempt + 1 < settings.llm_max_attempts
            except (TimeoutError, ValueError):
                output = None
                error = "invalid_or_timed_out"
                retry = attempt + 1 < settings.llm_max_attempts
            except Exception:
                output = None
                error = "evaluation_failed"
            if (
                error
                and not retry
                and error != "configuration_changed"
                and inputs.get("execution_policy", {}).get("fallback_enabled", False)
            ):
                output = deterministic_evaluation(inputs, profile, error)
                metadata = {**metadata, **evaluation_metadata("fallback")}
            await asyncio.to_thread(
                save_attempt,
                factory,
                run_id,
                token,
                evaluation_id,
                output,
                metadata,
                error,
                retry,
            )
            if not retry:
                return {}
            await asyncio.sleep(2**attempt)
        return {}

    builder = StateGraph(State)
    builder.add_node("dispatch", lambda state: {})
    builder.add_node("evaluate_persona", persona_node)
    builder.add_edge(START, "dispatch")
    builder.add_conditional_edges(
        "dispatch",
        lambda state: [
            Send("evaluate_persona", {"evaluation_id": eid}) for eid in state["ids"]
        ],
        ["evaluate_persona"],
    )
    builder.add_edge("evaluate_persona", END)
    graph = builder.compile()

    async def keep_lease():
        while True:
            await asyncio.sleep(10)
            if not await asyncio.to_thread(heartbeat, factory, run_id, token):
                return

    heartbeat_task = asyncio.create_task(keep_lease())
    try:
        ids = await asyncio.to_thread(work_ids, factory, run_id, token)
        if ids:
            await graph.ainvoke(
                {"ids": ids}, {"max_concurrency": settings.simulation_concurrency}
            )
        await asyncio.to_thread(finalize, factory, run_id, token)
    finally:
        heartbeat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat_task


async def worker_loop(factory, settings):
    warned = False
    while True:
        job = None
        stage = "persona adaptation queue"
        try:
            from app.services.persona_jobs import claim_adaptation, execute_adaptation

            adaptation = await asyncio.to_thread(claim_adaptation, factory)
            if adaptation:
                stage = "persona adaptation execution"
                await execute_adaptation(factory, settings, *adaptation)
            stage = "simulation queue"
            job = await asyncio.to_thread(claim, factory)
            if job:
                stage = "simulation execution"
                await execute_run(factory, settings, *job)
            warned = False
        except Exception as error:
            if job:
                with contextlib.suppress(Exception):
                    await asyncio.to_thread(expire_lease, factory, *job)
            # No provider exceptions, SQL parameters, inputs or secrets in logs.
            if not warned:
                # Some server/test logging configurations disable existing
                # module loggers. Operational worker failures must remain visible.
                logger.disabled = False
                logger.warning(
                    "Simulation worker unavailable (%s) during %s. %s",
                    type(error).__name__,
                    stage,
                    worker_failure_hint(error),
                )
                warned = True
        await asyncio.sleep(1)


def expire_lease(factory, run_id, token):
    with factory() as db:
        run = db.get(SimulationRun, run_id)
        if run and run.lease_token == token and run.status == "running":
            run.lease_until = now() - timedelta(seconds=1)
            db.commit()
