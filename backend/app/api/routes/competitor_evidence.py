from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from sqlalchemy import func, or_, select

from app.api.routes.auth import check_origin, get_current_user
from app.api.routes.products import owned_product
from app.db.session import DbSession
from app.models.auth import User
from app.models.competitor_evidence import CompetitorEvidence

router = APIRouter(tags=["competitor evidence"])
CurrentUser = Annotated[User, Depends(get_current_user)]
Csrf = Annotated[None, Depends(check_origin)]


class EvidenceFields(BaseModel):
    """Seller observations: names 200, descriptions 5000, offers 1000 chars."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "competitor_name": "TechZone BD",
                    "product_name": "Wireless Mouse",
                    "competitor_description": "Rechargeable mouse with quiet clicks.",
                    "category": "Electronics",
                    "price": "950.00",
                    "currency": "BDT",
                    "offer": "10% discount on two items",
                    "platform": "facebook",
                    "observed_at": "2025-11-20",
                    "notes": "Price observed on the seller's post.",
                }
            ]
        },
    )
    product_id: int | None = Field(default=None, gt=0)
    competitor_name: str = Field(min_length=1, max_length=200)
    product_name: str = Field(min_length=1, max_length=200)
    competitor_description: str | None = Field(default=None, max_length=5000)
    category: str | None = Field(default=None, max_length=200)
    price: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False
    )
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    offer: str | None = Field(default=None, max_length=1000)
    platform: str | None = Field(default=None, max_length=200)
    observed_at: date
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("observed_at")
    @classmethod
    def not_future(cls, value):
        if value > datetime.now(UTC).date():
            raise ValueError("Observation date cannot be in the future")
        return value

    @model_validator(mode="after")
    def price_currency_pair(self):
        if (self.price is None) != (self.currency is None):
            raise ValueError("Price and currency must be supplied together")
        return self


class EvidencePatch(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "price": "950.00",
                    "currency": "BDT",
                    "notes": "Price observed on the seller's post.",
                }
            ]
        },
    )
    product_id: int | None = Field(default=None, gt=0)
    competitor_name: str | None = Field(default=None, min_length=1, max_length=200)
    product_name: str | None = Field(default=None, min_length=1, max_length=200)
    competitor_description: str | None = Field(default=None, max_length=5000)
    category: str | None = Field(default=None, max_length=200)
    price: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False
    )
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    offer: str | None = Field(default=None, max_length=1000)
    platform: str | None = Field(default=None, max_length=200)
    observed_at: date | None = None
    notes: str | None = Field(default=None, max_length=5000)


class EvidenceResponse(EvidenceFields):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "seller_id": 1,
                    "product_id": None,
                    "competitor_name": "TechZone BD",
                    "product_name": "Wireless Mouse",
                    "competitor_description": "Rechargeable mouse with quiet clicks.",
                    "category": "Electronics",
                    "price": "950.00",
                    "currency": "BDT",
                    "offer": "10% discount on two items",
                    "platform": "facebook",
                    "observed_at": "2025-11-20",
                    "notes": "Price observed on the seller's post.",
                    "created_at": "2025-11-20T12:00:00Z",
                    "updated_at": "2025-11-20T12:00:00Z",
                    "deleted_at": None,
                }
            ]
        },
    )
    id: int
    seller_id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class EvidenceList(BaseModel):
    items: list[EvidenceResponse]
    total: int
    offset: int
    limit: int


RESPONSE_EXAMPLE = EvidenceResponse.model_config["json_schema_extra"]["examples"][0]
LIST_EXAMPLE = {"items": [RESPONSE_EXAMPLE], "total": 1, "offset": 0, "limit": 50}
SINGLE_RESPONSE = {"content": {"application/json": {"example": RESPONSE_EXAMPLE}}}
LIST_RESPONSE = {"content": {"application/json": {"example": LIST_EXAMPLE}}}
CREATE_EXAMPLES = {
    "observation": {
        "summary": "Competitor observation",
        "value": EvidenceFields.model_config["json_schema_extra"]["examples"][0],
    }
}
PATCH_EXAMPLES = {
    "price_update": {
        "summary": "Update the observed price",
        "value": EvidencePatch.model_config["json_schema_extra"]["examples"][0],
    }
}


def owned_evidence(evidence_id: int, user: User, db: DbSession, *, lock: bool = False):
    query = select(CompetitorEvidence).where(
        CompetitorEvidence.id == evidence_id,
        CompetitorEvidence.seller_id == user.id,
        CompetitorEvidence.deleted_at.is_(None),
    )
    if lock:
        query = query.with_for_update()
    record = db.scalar(query)
    if record is None:
        raise HTTPException(404, "Competitor evidence not found")
    return record


@router.post(
    "/competitor-evidence",
    status_code=201,
    response_model=EvidenceResponse,
    responses={201: SINGLE_RESPONSE},
)
def create_evidence(
    data: Annotated[EvidenceFields, Body(openapi_examples=CREATE_EXAMPLES)],
    user: CurrentUser,
    db: DbSession,
    _: Csrf,
):
    if data.product_id is not None:
        owned_product(data.product_id, user, db)
    record = CompetitorEvidence(**data.model_dump(), seller_id=user.id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get(
    "/competitor-evidence", response_model=EvidenceList, responses={200: LIST_RESPONSE}
)
def list_evidence(
    user: CurrentUser,
    db: DbSession,
    product_id: int | None = Query(default=None, gt=0),
    platform: str | None = Query(default=None, min_length=1, max_length=200),
    observed_at: date | None = None,
    observed_from: date | None = None,
    observed_to: date | None = None,
    q: str | None = Query(default=None, min_length=1, max_length=200),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    if observed_from and observed_to and observed_from > observed_to:
        raise HTTPException(422, "observed_from must not be after observed_to")
    filters = [
        CompetitorEvidence.seller_id == user.id,
        CompetitorEvidence.deleted_at.is_(None),
    ]
    if product_id is not None:
        filters.append(CompetitorEvidence.product_id == product_id)
    if platform is not None:
        filters.append(
            func.lower(CompetitorEvidence.platform) == platform.strip().lower()
        )
    if observed_at is not None:
        filters.append(CompetitorEvidence.observed_at == observed_at)
    if observed_from is not None:
        filters.append(CompetitorEvidence.observed_at >= observed_from)
    if observed_to is not None:
        filters.append(CompetitorEvidence.observed_at <= observed_to)
    if q is not None:
        term = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        if not term:
            raise HTTPException(422, "Search must not be blank")
        filters.append(
            or_(
                CompetitorEvidence.competitor_name.ilike(f"%{term}%", escape="\\"),
                CompetitorEvidence.product_name.ilike(f"%{term}%", escape="\\"),
            )
        )
    total = db.scalar(
        select(func.count()).select_from(CompetitorEvidence).where(*filters)
    )
    items = db.scalars(
        select(CompetitorEvidence)
        .where(*filters)
        .order_by(CompetitorEvidence.created_at.desc(), CompetitorEvidence.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.get(
    "/competitor-evidence/{evidence_id}",
    response_model=EvidenceResponse,
    responses={200: SINGLE_RESPONSE},
)
def get_evidence(evidence_id: int, user: CurrentUser, db: DbSession):
    return owned_evidence(evidence_id, user, db)


@router.patch(
    "/competitor-evidence/{evidence_id}",
    response_model=EvidenceResponse,
    responses={200: SINGLE_RESPONSE},
)
def update_evidence(
    evidence_id: int,
    data: Annotated[EvidencePatch, Body(openapi_examples=PATCH_EXAMPLES)],
    user: CurrentUser,
    db: DbSession,
    _: Csrf,
):
    record = owned_evidence(evidence_id, user, db, lock=True)
    changes = data.model_dump(exclude_unset=True)
    current = {name: getattr(record, name) for name in EvidenceFields.model_fields}
    try:
        validated = EvidenceFields.model_validate(current | changes)
    except ValidationError:
        raise HTTPException(422, "Invalid competitor evidence") from None
    if "product_id" in changes and validated.product_id is not None:
        owned_product(validated.product_id, user, db)
    for name in changes:
        setattr(record, name, getattr(validated, name))
    record.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/competitor-evidence/{evidence_id}", status_code=204)
def delete_evidence(evidence_id: int, user: CurrentUser, db: DbSession, _: Csrf):
    record = owned_evidence(evidence_id, user, db, lock=True)
    record.deleted_at = record.updated_at = datetime.now(UTC)
    db.commit()
    return Response(status_code=204)
