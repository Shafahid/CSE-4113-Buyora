"""Seller-owned report history, immutable search, and comparison helpers."""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select

from app.models import SimulationRun
from app.services.simulation_runs import TERMINAL, utc_time
from app.services.trust_scoring import DIMENSIONS


def owned_report(db, report_id: str, seller_id: int, *, lock: bool = False):
    query = select(SimulationRun).where(
        SimulationRun.id == report_id,
        SimulationRun.seller_id == seller_id,
    )
    if lock:
        query = query.with_for_update()
    run = db.scalar(query)
    if not run or run.status not in TERMINAL or not run.report:
        raise HTTPException(404, "Report not found")
    return run


def score_summary(run):
    reactions = [
        reaction
        for reaction in (run.report or {}).get("reactions", [])
        if reaction.get("status") == "complete"
        and isinstance(reaction.get("scores"), list)
        and len(reaction["scores"]) == len(DIMENSIONS)
    ]
    if not reactions:
        return None, {}
    dimensions = {
        name: round(
            sum(float(reaction["scores"][index]) for reaction in reactions)
            / len(reactions),
            1,
        )
        for index, name in enumerate(DIMENSIONS)
    }
    overall = round(sum(dimensions.values()) / len(dimensions), 1)
    return overall, dimensions


def report_summary(run):
    report = run.report or {}
    coverage = report.get("coverage", {})
    overall, dimensions = score_summary(run)
    return {
        "id": run.id,
        "title": report.get("title") or run.inputs["product"]["name"],
        "status": run.status,
        "mode": report.get("mode") or run.inputs.get("mode", "custom"),
        "persona_count": run.expected_personas,
        "completed": coverage.get("completed", 0),
        "failed": coverage.get("failed", 0),
        "overall_score": overall,
        "dimension_scores": dimensions,
        "fallback_count": report.get("fallbackCount", 0),
        "created_at": utc_time(run.created_at),
        "completed_at": utc_time(run.completed_at),
    }


def report_history(
    db,
    seller_id: int,
    *,
    query: str | None = None,
    status: str | None = None,
    mode: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    oldest_first: bool = False,
):
    statement = select(SimulationRun).where(
        SimulationRun.seller_id == seller_id,
        SimulationRun.status.in_(TERMINAL),
        SimulationRun.report.is_not(None),
    )
    if created_from:
        statement = statement.where(SimulationRun.created_at >= created_from)
    if created_to:
        statement = statement.where(SimulationRun.created_at <= created_to)
    order = (
        SimulationRun.created_at.asc()
        if oldest_first
        else SimulationRun.created_at.desc()
    )
    runs = list(db.scalars(statement.order_by(order, SimulationRun.id)))
    if status:
        runs = [run for run in runs if run.status == status]
    if mode:
        runs = [
            run
            for run in runs
            if ((run.report or {}).get("mode") or run.inputs.get("mode", "custom"))
            == mode
        ]
    if query:
        needle = query.casefold().strip()

        def matches(run):
            source = run.inputs
            values = (
                source.get("product", {}).get("name", ""),
                source.get("product", {}).get("category", ""),
                source.get("post", {}).get("headline", ""),
                source.get("post", {}).get("body", ""),
            )
            return any(needle in str(value).casefold() for value in values)

        runs = [run for run in runs if matches(run)]
    return runs


def compare_reports(runs):
    summaries = [report_summary(run) for run in runs]
    if any(summary["overall_score"] is None for summary in summaries):
        raise HTTPException(409, "Both reports need completed buyer evaluations")
    dimensions = [
        {
            "dimension": dimension,
            "values": {
                summary["id"]: summary["dimension_scores"][dimension]
                for summary in summaries
            },
            "difference": round(
                summaries[1]["dimension_scores"][dimension]
                - summaries[0]["dimension_scores"][dimension],
                1,
            ),
        }
        for dimension in DIMENSIONS
    ]
    return {
        "reports": [
            {
                key: summary[key]
                for key in (
                    "id",
                    "title",
                    "persona_count",
                    "overall_score",
                    "created_at",
                )
            }
            for summary in summaries
        ],
        "dimensions": dimensions,
        "persona_count_difference": (
            summaries[1]["persona_count"] - summaries[0]["persona_count"]
        ),
        "overall_score_difference": round(
            summaries[1]["overall_score"] - summaries[0]["overall_score"], 1
        ),
    }
