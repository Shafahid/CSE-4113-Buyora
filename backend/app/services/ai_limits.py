"""Database-backed quotas. Reservations commit atomically with admitted jobs."""

import json
import math
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select

from app.models import AIRequestReservation, User
from app.schemas.phase2 import ExecutionBudget


def lock_ai_seller(db, seller_id):
    # Always acquire before resource locks, matching simulation lock order.
    db.execute(
        select(User.id).where(User.id == seller_id).with_for_update()
    ).scalar_one()


def reserve_ai_request(db, seller_id, kind, resource_id, settings, payload):
    """Caller holds seller lock until job + reservation + dispatch commit together.

    Count all optional AI kinds together. Never refund uncertain provider usage.
    No retries are included: every further provider attempt needs new admission.
    """
    now = datetime.now(UTC)
    minute_start = now - timedelta(seconds=60)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    scope = AIRequestReservation.seller_id == seller_id
    count, oldest = db.execute(
        select(func.count(), func.min(AIRequestReservation.created_at)).where(
            scope, AIRequestReservation.created_at > minute_start
        )
    ).one()
    if count >= settings.phase2_ai_requests_per_minute:
        oldest = oldest.replace(tzinfo=UTC) if oldest.tzinfo is None else oldest
        retry = max(
            1, math.ceil((oldest + timedelta(seconds=60) - now).total_seconds())
        )
        raise HTTPException(
            429, "AI request rate limit reached", headers={"Retry-After": str(retry)}
        )
    policy = ExecutionBudget(
        max_input_tokens=settings.phase2_ai_max_input_tokens,
        max_output_tokens=settings.phase2_ai_max_output_tokens,
        timeout_seconds=settings.phase2_ai_timeout_seconds,
    )
    # UTF-8 bytes conservatively bound text input size before model tokenization.
    if (
        len(json.dumps(payload, ensure_ascii=False, default=str).encode())
        > policy.max_input_tokens
    ):
        raise HTTPException(422, "AI input exceeds the configured request budget")
    reserved = policy.max_input_tokens + policy.max_output_tokens
    spent = db.scalar(
        select(func.coalesce(func.sum(AIRequestReservation.reserved_tokens), 0)).where(
            scope, AIRequestReservation.created_at >= day_start
        )
    )
    if spent + reserved > settings.phase2_ai_daily_token_budget:
        retry = math.ceil((day_start + timedelta(days=1) - now).total_seconds())
        raise HTTPException(
            429, "Daily AI token budget reached", headers={"Retry-After": str(retry)}
        )
    row = AIRequestReservation(
        id=str(uuid4()),
        seller_id=seller_id,
        kind=kind,
        resource_id=resource_id,
        reserved_tokens=reserved,
        policy=policy.model_dump(),
        created_at=now,
    )
    db.add(row)
    db.flush()
    return row


def request_budget(db, kind, resource_id):
    row = db.scalar(
        select(AIRequestReservation).where(
            AIRequestReservation.kind == kind,
            AIRequestReservation.resource_id == resource_id,
        )
    )
    if row is None:
        raise ValueError("AI request has no budget reservation")
    return ExecutionBudget.model_validate(row.policy)
