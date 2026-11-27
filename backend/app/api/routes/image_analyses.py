from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select

from app.api.routes.auth import check_origin, get_current_user
from app.api.routes.products import image_revision, owned_product
from app.db.session import DbSession
from app.models.auth import User
from app.models.product_image import ProductImage
from app.models.product_image_analysis import ProductImageAnalysis
from app.services.image_analysis import ImageAnalysisResult
from app.services.processing_admission import (
    DurableProcessingAdmission,
    get_processing_admission,
    processing_is_ready,
)

router = APIRouter(tags=["product image analysis"])
CurrentUser = Annotated[User, Depends(get_current_user)]
Csrf = Annotated[None, Depends(check_origin)]


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid", json_schema_extra={"examples": [{"language": "en"}]}
    )
    language: Literal["en", "bn"] = "en"


class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    original_image_id: int
    language: Literal["en", "bn"]
    status: Literal["pending", "processing", "completed", "failed"]
    analysis_result: ImageAnalysisResult | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    processing_available: bool = False
    image_revision: str | None = None
    is_current_image: bool | None = None


class AnalysisList(BaseModel):
    items: list[AnalysisResponse]
    total: int
    limit: int
    offset: int


def owned_image(
    product_id: int, image_id: int, user: User, db: DbSession, *, lock: bool = False
):
    owned_product(product_id, user, db)
    query = select(ProductImage).where(
        ProductImage.id == image_id, ProductImage.product_id == product_id
    )
    if lock:
        query = query.with_for_update()
    image = db.scalar(query)
    if image is None:
        raise HTTPException(404, "Image not found")
    return image


def render_analysis(analysis, current_key, processing_available=False):
    result = AnalysisResponse.model_validate(analysis)
    key = analysis.snapshot_storage_key
    return result.model_copy(
        update={
            "processing_available": processing_available,
            "image_revision": image_revision(key) if key else None,
            "is_current_image": (key == current_key)
            if key and current_key
            else (False if key else None),
        }
    )


def current_image_key(product_id, image_id, user, db):
    owned_product(product_id, user, db)
    return db.scalar(
        select(ProductImage.storage_key).where(
            ProductImage.id == image_id, ProductImage.product_id == product_id
        )
    )


@router.post(
    "/products/{product_id}/images/{image_id}/analyses",
    status_code=202,
    response_model=AnalysisResponse,
)
def request_analysis(
    product_id: int,
    image_id: int,
    data: AnalysisRequest,
    user: CurrentUser,
    db: DbSession,
    _: Csrf,
    admission: Annotated[
        DurableProcessingAdmission | None, Depends(get_processing_admission)
    ],
):
    image = owned_image(product_id, image_id, user, db, lock=True)
    if not isinstance(admission, DurableProcessingAdmission):
        raise HTTPException(503, "Image analysis service is not configured")
    analysis = ProductImageAnalysis(
        product_id=product_id,
        image_id=image_id,
        original_image_id=image_id,
        snapshot_storage_key=image.storage_key,
        seller_id=user.id,
        language=data.language,
        status="pending",
    )
    try:
        admission.verify_ready(db, "image_analysis")
        db.add(analysis)
        db.flush()
        admission.enqueue(db, "image_analysis", analysis.id)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(503, "Image analysis service is not configured") from None
    db.refresh(analysis)
    return render_analysis(analysis, image.storage_key).model_copy(
        update={"processing_available": True}
    )


@router.get(
    "/products/{product_id}/images/{image_id}/analyses", response_model=AnalysisList
)
def list_analyses(
    product_id: int,
    image_id: int,
    user: CurrentUser,
    db: DbSession,
    admission: Annotated[
        DurableProcessingAdmission | None, Depends(get_processing_admission)
    ],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    current_key = current_image_key(product_id, image_id, user, db)
    available = processing_is_ready(admission, db, "image_analysis")
    criteria = (
        ProductImageAnalysis.seller_id == user.id,
        ProductImageAnalysis.product_id == product_id,
        ProductImageAnalysis.original_image_id == image_id,
    )
    total = db.scalar(
        select(func.count()).select_from(ProductImageAnalysis).where(*criteria)
    )
    items = db.scalars(
        select(ProductImageAnalysis)
        .where(*criteria)
        .order_by(
            ProductImageAnalysis.created_at.desc(), ProductImageAnalysis.id.desc()
        )
        .offset(offset)
        .limit(limit)
    ).all()
    if current_key is None and total == 0:
        raise HTTPException(404, "Image not found")
    return {
        "items": [render_analysis(item, current_key, available) for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/products/{product_id}/images/{image_id}/analyses/{analysis_id}",
    response_model=AnalysisResponse,
)
def get_analysis(
    product_id: int,
    image_id: int,
    analysis_id: int,
    user: CurrentUser,
    db: DbSession,
    admission: Annotated[
        DurableProcessingAdmission | None, Depends(get_processing_admission)
    ],
):
    current_key = current_image_key(product_id, image_id, user, db)
    available = processing_is_ready(admission, db, "image_analysis")
    result = db.scalar(
        select(ProductImageAnalysis).where(
            ProductImageAnalysis.id == analysis_id,
            ProductImageAnalysis.seller_id == user.id,
            ProductImageAnalysis.product_id == product_id,
            ProductImageAnalysis.original_image_id == image_id,
        )
    )
    if result is None:
        raise HTTPException(404, "Analysis not found")
    return render_analysis(result, current_key, available)
