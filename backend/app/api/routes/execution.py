from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response
from sqlalchemy import delete, select

from app.api.routes.simulations import Csrf, CurrentUser
from app.db.session import DbSession
from app.models import (
    PersonaEvaluation,
    Simulation,
    SimulationCache,
    SimulationPersona,
    SimulationRun,
)
from app.schemas.execution import (
    BulkRetryRequest,
    PersonaAdaptRequest,
    PersonaAdaptResponse,
    PreviewResponse,
    ReportChanges,
    RetryRequest,
    RevisionRequest,
    RunCreate,
    RunPreview,
    RunProgress,
    RunResponse,
    SimulationOptions,
)
from app.services.persona_catalog import profiles
from app.services.persona_jobs import (
    adaptation_response,
    owned_adaptation,
    start_adaptation,
)
from app.services.report_insights import revised_caption
from app.services.simulation_runs import (
    TERMINAL,
    can_retry,
    create_run,
    evaluations,
    now,
    owned_run,
    prepare_inputs,
    response,
    utc_time,
)

router = APIRouter(tags=["simulation execution"])


@router.post(
    "/persona-adaptations", response_model=PersonaAdaptResponse, status_code=202
)
def adapt_personas(
    data: PersonaAdaptRequest,
    request: Request,
    user: CurrentUser,
    db: DbSession,
    _: Csrf,
):
    return start_adaptation(db, user.id, data, request.app.state.settings)


@router.get("/persona-adaptations/{job_id}", response_model=PersonaAdaptResponse)
def get_adaptation(job_id: UUID, user: CurrentUser, db: DbSession):
    return adaptation_response(owned_adaptation(db, str(job_id), user.id))


@router.post("/simulation-runs/preview", response_model=PreviewResponse)
def preview_run(
    data: RunPreview, request: Request, user: CurrentUser, db: DbSession, _: Csrf
):
    _, inputs, fingerprint = prepare_inputs(
        db, user.id, data, request.app.state.settings
    )
    if data.product_id != inputs["product_id"]:
        raise HTTPException(404, "Active product post version not found")
    if data.post != inputs["post"]:
        return {"match": False}
    cached = db.get(SimulationCache, (user.id, fingerprint))
    if not cached:
        return {"match": False}
    run = owned_run(db, cached.run_id, user.id)
    rows = evaluations(db, run.id)
    return {
        "match": True,
        "run_id": run.id,
        "status": run.status,
        "completed": sum(e.status == "completed" for e in rows),
        "total": len(rows),
        "created_at": utc_time(run.created_at),
    }


@router.post("/simulation-runs/{run_id}/retry-failed", response_model=RunResponse)
def retry_failed(
    run_id: UUID, data: BulkRetryRequest, user: CurrentUser, db: DbSession, _: Csrf
):
    run = owned_run(db, str(run_id), user.id, lock=True)
    rows = evaluations(db, run.id)
    # Persist the operation key so a delayed HTTP retry cannot pay for work twice,
    # even if the first retry has already finished by the time it arrives.
    if any(
        event.get("request_id") == str(data.request_id)
        for row in rows
        for event in row.history
    ):
        return response(db, run)
    if run.status not in TERMINAL:
        return response(db, run)
    eligible = [row for row in rows if row.status == "failed" and can_retry(row)]
    if not eligible:
        raise HTTPException(
            409, "No perspectives can be retried. Review the report for next steps."
        )
    eligible[0].history = [
        *eligible[0].history,
        {
            "event": "retry_requested",
            "request_id": str(data.request_id),
            "evaluation_ids": [row.id for row in eligible],
            "at": now().isoformat(),
        },
    ]
    for row in eligible:
        row.status = "queued"
        row.error_code = None
        row.updated_at = now()
    queue_retry(db, run)
    return response(db, run)


def queue_retry(db, run):
    run.status = "queued"
    run.started_at = None
    run.completed_at = None
    run.updated_at = now()
    simulation = db.get(Simulation, run.simulation_id)
    simulation.status = "queued"
    simulation.started_at = None
    simulation.completed_at = None
    db.commit()


@router.get("/simulation-options", response_model=SimulationOptions)
def options(request: Request, user: CurrentUser):
    return {
        "max_personas": request.app.state.settings.simulation_max_personas,
        "profiles": profiles(),
    }


@router.post("/simulation-runs", response_model=RunResponse, status_code=202)
def start_run(
    data: RunCreate,
    request: Request,
    user: CurrentUser,
    db: DbSession,
    _: Csrf,
    http_response: Response,
):
    result = create_run(db, user.id, data, request.app.state.settings)
    if result.status in TERMINAL:
        http_response.status_code = 200
    return result


@router.get("/simulation-runs", response_model=list[RunResponse])
def list_runs(
    user: CurrentUser,
    db: DbSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
):
    # Use the same ownership chain for listing and direct retrieval.
    from app.models import Post, PostVersion, Product

    runs = db.scalars(
        select(SimulationRun)
        .join(Simulation, Simulation.id == SimulationRun.simulation_id)
        .join(PostVersion, PostVersion.id == Simulation.post_version_id)
        .join(Post, Post.id == PostVersion.post_id)
        .join(Product, Product.id == Post.product_id)
        .where(SimulationRun.seller_id == user.id, Product.deleted_at.is_(None))
        .order_by(SimulationRun.created_at.desc(), SimulationRun.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return [response(db, run) for run in runs]


@router.get("/simulation-runs/{run_id}", response_model=RunResponse)
def get_run(run_id: UUID, user: CurrentUser, db: DbSession):
    return response(db, owned_run(db, str(run_id), user.id))


@router.get("/simulation-runs/{run_id}/progress", response_model=RunProgress)
def get_progress(run_id: UUID, user: CurrentUser, db: DbSession):
    return response(db, owned_run(db, str(run_id), user.id), include_report=False)


@router.post("/simulation-runs/{run_id}/retry", response_model=RunResponse)
def retry_persona(
    run_id: UUID, data: RetryRequest, user: CurrentUser, db: DbSession, _: Csrf
):
    run = owned_run(db, str(run_id), user.id, lock=True)
    if run.status not in TERMINAL:
        # A double click or retried HTTP request must not queue another call.
        return response(db, run)
    row = db.get(PersonaEvaluation, data.evaluation_id)
    if not row or row.run_id != run.id:
        raise HTTPException(404, "Evaluation not found")
    if (
        row.status == "completed"
        and (row.output or {}).get("evaluation_source") != "fallback"
    ):
        return response(db, run)
    if not can_retry(row):
        raise HTTPException(
            409,
            "This perspective needs attention before another run. "
            "Review the report for next steps.",
        )
    row.status = "queued"
    row.error_code = None
    row.updated_at = now()
    queue_retry(db, run)
    return response(db, run)


@router.patch("/simulation-runs/{run_id}/report", response_model=RunResponse)
def update_report(
    run_id: UUID, data: ReportChanges, user: CurrentUser, db: DbSession, _: Csrf
):
    run = owned_run(db, str(run_id), user.id, lock=True)
    if run.status not in TERMINAL or not run.report:
        raise HTTPException(409, "Wait for the simulation to finish")
    run.report = {**run.report, **data.model_dump()}
    db.commit()
    return response(db, run)


@router.post("/simulation-runs/{run_id}/revise", response_model=RunResponse)
def revise_report(
    run_id: UUID, data: RevisionRequest, user: CurrentUser, db: DbSession, _: Csrf
):
    run = owned_run(db, str(run_id), user.id, lock=True)
    if run.status not in TERMINAL or not run.report:
        raise HTTPException(409, "Wait for the simulation to finish")
    from app.services.report_insights import recommendations

    recs = run.report.get("recommendations") or recommendations(
        run.inputs, evaluations(db, run.id)
    )
    try:
        body = revised_caption(run.inputs, data.applied, recs)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    run.report = {
        **run.report,
        "revised": body,
        "applied": data.applied,
        "recommendations": recs,
    }
    db.commit()
    return response(db, run)


@router.delete("/simulation-runs/{run_id}", status_code=204)
def delete_report(run_id: UUID, user: CurrentUser, db: DbSession, _: Csrf):
    run = owned_run(db, str(run_id), user.id, lock=True)
    if run.status not in TERMINAL:
        raise HTTPException(409, "Wait for the simulation to finish before deleting it")
    # Explicit order also works in SQLite, which omits cross-schema FKs.
    simulation_id = run.simulation_id
    db.execute(delete(SimulationCache).where(SimulationCache.run_id == run.id))
    db.execute(delete(PersonaEvaluation).where(PersonaEvaluation.run_id == run.id))
    db.delete(run)
    db.flush()
    db.execute(
        delete(SimulationPersona).where(
            SimulationPersona.simulation_id == simulation_id
        )
    )
    db.delete(db.get(Simulation, simulation_id))
    db.commit()
    return Response(status_code=204)
