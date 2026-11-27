from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select

from app.api.routes.auth import check_origin, get_current_user
from app.api.routes.products import owned_product
from app.db.session import DbSession
from app.models.auth import User
from app.models.product_image import ProductImage
from app.models.product_image_analysis import ProductImageAnalysis
from app.services.image_analysis import ImageAnalysisResult

router = APIRouter(tags=["product image analysis"])
CurrentUser = Annotated[User, Depends(get_current_user)]
Csrf = Annotated[None, Depends(check_origin)]


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
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


class AnalysisList(BaseModel):
    items: list[AnalysisResponse]
    total: int
    limit: int
    offset: int


def owned_image(product_id: int, image_id: int, user: User, db: DbSession):
    owned_product(product_id, user, db)
    image = db.scalar(
        select(ProductImage).where(
            ProductImage.id == image_id, ProductImage.product_id == product_id
        )
    )
    if image is None:
        raise HTTPException(404, "Image not found")
    return image


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
):
    owned_image(product_id, image_id, user, db)
    analysis = ProductImageAnalysis(
        product_id=product_id,
        image_id=image_id,
        original_image_id=image_id,
        seller_id=user.id,
        language=data.language,
        status="pending",
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


@router.get(
    "/products/{product_id}/images/{image_id}/analyses", response_model=AnalysisList
)
def list_analyses(
    product_id: int,
    image_id: int,
    user: CurrentUser,
    db: DbSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    owned_image(product_id, image_id, user, db)
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
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get(
    "/products/{product_id}/images/{image_id}/analyses/{analysis_id}",
    response_model=AnalysisResponse,
)
def get_analysis(
    product_id: int, image_id: int, analysis_id: int, user: CurrentUser, db: DbSession
):
    owned_image(product_id, image_id, user, db)
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
    return result
