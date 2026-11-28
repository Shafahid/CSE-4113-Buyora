from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select

from app.api.routes.auth import check_origin, get_current_user
from app.api.routes.products import owned_product
from app.db.session import DbSession
from app.models.auth import User
from app.models.competitor_evidence import CompetitorEvidence
from app.models.market_analysis import MarketAnalysis
from app.schemas.phase2 import AIMetadata, ExecutionBudget
from app.services.ai_limits import lock_ai_seller, reserve_ai_request
from app.services.market_analysis import (
    EvidenceSnapshot,
    MarketInput,
    MarketResult,
    ProductSnapshot,
    price_observations,
)
from app.services.processing_admission import (
    DurableProcessingAdmission,
    get_processing_admission,
)

router = APIRouter(tags=["market analyses"])
CurrentUser = Annotated[User, Depends(get_current_user)]
Csrf = Annotated[None, Depends(check_origin)]


class MarketRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"competitor_evidence_ids": [1, 2], "language": "en"}]
        },
    )
    competitor_evidence_ids: list[int] = Field(min_length=1, max_length=20)
    language: Literal["en", "bn"] = "en"

    @field_validator("competitor_evidence_ids")
    @classmethod
    def valid_ids(cls, ids):
        if any(i <= 0 for i in ids) or len(set(ids)) != len(ids):
            raise ValueError("Evidence IDs must be positive and unique")
        return ids


class MarketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    schema_version: Literal["1.0"] = "1.0"
    id: int
    product_id: int
    status: Literal["pending", "processing", "completed", "failed"]
    language: Literal["en", "bn"]
    input_snapshot: MarketInput
    analysis_result: MarketResult | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    price_observations: list[dict]
    evidence_notice: str = (
        "Competitor information is seller-provided and not independently verified."
    )
    interpretations_require_review: bool = True
    processing_metadata: AIMetadata | None = None


def render(row):
    snapshot = MarketInput.model_validate(row.input_snapshot)
    if snapshot.comparison_date is None:
        snapshot.comparison_date = row.created_at.date()
    return MarketResponse.model_validate(
        {
            "id": row.id,
            "product_id": row.product_id,
            "status": row.status,
            "language": row.language,
            "input_snapshot": snapshot,
            "analysis_result": row.analysis_result,
            "error_message": row.error_message,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "completed_at": row.completed_at,
            "price_observations": price_observations(snapshot),
            "processing_metadata": row.processing_metadata,
        }
    )


class MarketList(BaseModel):
    items: list[MarketResponse]
    total: int
    offset: int
    limit: int


@router.post(
    "/products/{product_id}/market-analyses",
    status_code=202,
    response_model=MarketResponse,
)
def create_analysis(
    product_id: int,
    data: MarketRequest,
    request: Request,
    user: CurrentUser,
    db: DbSession,
    _: Csrf,
    admission: Annotated[
        DurableProcessingAdmission | None, Depends(get_processing_admission)
    ],
):
    lock_ai_seller(db, user.id)
    product = owned_product(product_id, user, db)
    records = db.scalars(
        select(CompetitorEvidence).where(
            CompetitorEvidence.id.in_(data.competitor_evidence_ids),
            CompetitorEvidence.seller_id == user.id,
            CompetitorEvidence.deleted_at.is_(None),
        )
    ).all()
    by_id = {item.id: item for item in records}
    if len(by_id) != len(data.competitor_evidence_ids):
        raise HTTPException(404, "Competitor evidence not found")
    # A worker must be explicitly installed before accepting durable work.
    if not isinstance(admission, DurableProcessingAdmission):
        raise HTTPException(503, "Market analysis service is not configured")
    snapshot = MarketInput(
        product=ProductSnapshot.model_validate(product, from_attributes=True),
        competitors=[
            EvidenceSnapshot.model_validate(by_id[i], from_attributes=True)
            for i in data.competitor_evidence_ids
        ],
        language=data.language,
        comparison_date=datetime.now(UTC).date(),
        max_evidence_age_days=request.app.state.settings.market_evidence_max_age_days,
    )
    analysis = MarketAnalysis(
        product_id=product.id,
        seller_id=user.id,
        language=data.language,
        status="pending",
        input_snapshot=snapshot.model_dump(mode="json"),
    )
    try:
        admission.verify_ready(db, "market_analysis")
        db.add(analysis)
        db.flush()
        reservation = reserve_ai_request(
            db,
            user.id,
            "market_analysis",
            analysis.id,
            request.app.state.settings,
            snapshot.model_dump(mode="json"),
        )
        snapshot.budget = ExecutionBudget.model_validate(reservation.policy)
        analysis.input_snapshot = snapshot.model_dump(mode="json")
        admission.enqueue(db, "market_analysis", analysis.id)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(503, "Market analysis service is not configured") from None
    db.refresh(analysis)
    return render(analysis)


@router.get("/products/{product_id}/market-analyses", response_model=MarketList)
def list_analyses(
    product_id: int,
    user: CurrentUser,
    db: DbSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    owned_product(product_id, user, db)
    criteria = (
        MarketAnalysis.seller_id == user.id,
        MarketAnalysis.product_id == product_id,
    )
    total = db.scalar(select(func.count()).select_from(MarketAnalysis).where(*criteria))
    rows = db.scalars(
        select(MarketAnalysis)
        .where(*criteria)
        .order_by(MarketAnalysis.created_at.desc(), MarketAnalysis.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return {
        "items": [render(row) for row in rows],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get(
    "/products/{product_id}/market-analyses/{analysis_id}",
    response_model=MarketResponse,
)
def get_analysis(product_id: int, analysis_id: int, user: CurrentUser, db: DbSession):
    owned_product(product_id, user, db)
    row = db.scalar(
        select(MarketAnalysis).where(
            MarketAnalysis.id == analysis_id,
            MarketAnalysis.product_id == product_id,
            MarketAnalysis.seller_id == user.id,
        )
    )
    if row is None:
        raise HTTPException(404, "Market analysis not found")
    return render(row)
