from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select

from app.api.routes.auth import check_origin, get_current_user
from app.api.routes.posts import owned_post
from app.db.session import DbSession
from app.models.auth import User
from app.models.platform_variant import PlatformVariant, PlatformVariantRevision
from app.models.post import PostVersion
from app.services.ai_limits import lock_ai_seller, reserve_ai_request
from app.services.platform_content import Platform, VariantContent
from app.services.processing_admission import (
    DurableProcessingAdmission,
    get_processing_admission,
    processing_is_ready,
)

router = APIRouter(tags=["platform variants"])
CurrentUser = Annotated[User, Depends(get_current_user)]
Csrf = Annotated[None, Depends(check_origin)]


class VariantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    source_version_id: int = Field(gt=0)
    platform: Platform
    language: Literal["en", "bn"] = "en"
    preferences: str | None = Field(default=None, max_length=2000)
    content: VariantContent | None = None


class RevisionResponse(VariantContent):
    model_config = ConfigDict(from_attributes=True)
    id: int
    variant_id: int
    revision_number: int
    origin: Literal["seller", "ai"]
    created_at: datetime


class VariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    schema_version: Literal["1.0"] = "1.0"
    id: int
    source_version_id: int
    platform: Platform
    language: Literal["en", "bn"]
    preferences: str | None
    status: Literal["pending", "processing", "ready", "failed"]
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    processing_available: bool = False
    latest_revision: RevisionResponse | None = None


class VariantList(BaseModel):
    items: list[VariantResponse]
    total: int
    offset: int
    limit: int


def owned_variant(post_id: int, variant_id: int, user: User, db: DbSession, lock=False):
    owned_post(post_id, user, db)
    query = (
        select(PlatformVariant)
        .join(PostVersion, PostVersion.id == PlatformVariant.source_version_id)
        .where(PostVersion.post_id == post_id, PlatformVariant.id == variant_id)
    )
    if lock:
        query = query.with_for_update(of=PlatformVariant)
    result = db.scalar(query)
    if result is None:
        raise HTTPException(404, "Variant not found")
    return result


def response(db, variant, processing_available=False):
    latest = db.scalar(
        select(PlatformVariantRevision)
        .where(PlatformVariantRevision.variant_id == variant.id)
        .order_by(PlatformVariantRevision.revision_number.desc())
        .limit(1)
    )
    return VariantResponse.model_validate(variant).model_copy(
        update={
            "processing_available": processing_available,
            "latest_revision": RevisionResponse.model_validate(latest)
            if latest
            else None,
        }
    )


@router.post(
    "/posts/{post_id}/variants", status_code=201, response_model=VariantResponse
)
def create_variant(
    post_id: int,
    data: VariantCreate,
    request: Request,
    user: CurrentUser,
    db: DbSession,
    _: Csrf,
    admission: Annotated[
        DurableProcessingAdmission | None, Depends(get_processing_admission)
    ],
):
    lock_ai_seller(db, user.id)
    owned_post(post_id, user, db, lock=True)
    source = db.scalar(
        select(PostVersion).where(
            PostVersion.id == data.source_version_id, PostVersion.post_id == post_id
        )
    )
    if source is None:
        raise HTTPException(404, "Post version not found")
    if data.content is None and not isinstance(admission, DurableProcessingAdmission):
        raise HTTPException(503, "Platform generation service is not configured")
    variant = PlatformVariant(
        source_version_id=source.id,
        platform=data.platform,
        language=data.language,
        preferences=data.preferences,
        status="ready" if data.content else "pending",
    )
    try:
        if data.content is None:
            admission.verify_ready(db, "platform_generation")
        db.add(variant)
        db.flush()
        if data.content:
            db.add(
                PlatformVariantRevision(
                    variant_id=variant.id,
                    revision_number=1,
                    origin="seller",
                    **data.content.model_dump(),
                )
            )
        else:
            reserve_ai_request(
                db,
                user.id,
                "platform_generation",
                variant.id,
                request.app.state.settings,
                {
                    "post": {
                        key: getattr(source, key)
                        for key in (
                            "headline",
                            "body",
                            "offer",
                            "call_to_action",
                            "hashtags",
                        )
                    },
                    "preferences": data.preferences,
                },
            )
            admission.enqueue(db, "platform_generation", variant.id)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        if data.content is None:
            raise HTTPException(
                503, "Platform generation service is not configured"
            ) from None
        raise
    db.refresh(variant)
    result = response(db, variant)
    return (
        result.model_copy(update={"processing_available": True})
        if data.content is None
        else result
    )


@router.get("/posts/{post_id}/variants", response_model=VariantList)
def list_variants(
    post_id: int,
    user: CurrentUser,
    db: DbSession,
    admission: Annotated[
        DurableProcessingAdmission | None, Depends(get_processing_admission)
    ],
    platform: Platform | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    owned_post(post_id, user, db)
    available = processing_is_ready(admission, db, "platform_generation")
    conditions = [PostVersion.post_id == post_id]
    if platform:
        conditions.append(PlatformVariant.platform == platform)
    query = (
        select(PlatformVariant)
        .join(PostVersion, PostVersion.id == PlatformVariant.source_version_id)
        .where(*conditions)
    )
    total = db.scalar(
        select(func.count())
        .select_from(PlatformVariant)
        .join(PostVersion, PostVersion.id == PlatformVariant.source_version_id)
        .where(*conditions)
    )
    variants = db.scalars(
        query.order_by(PlatformVariant.created_at.desc(), PlatformVariant.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return {
        "items": [response(db, v, available) for v in variants],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/posts/{post_id}/variants/{variant_id}", response_model=VariantResponse)
def get_variant(
    post_id: int,
    variant_id: int,
    user: CurrentUser,
    db: DbSession,
    admission: Annotated[
        DurableProcessingAdmission | None, Depends(get_processing_admission)
    ],
):
    variant = owned_variant(post_id, variant_id, user, db)
    available = processing_is_ready(admission, db, "platform_generation")
    return response(db, variant, available)


@router.post(
    "/posts/{post_id}/variants/{variant_id}/revisions",
    status_code=201,
    response_model=RevisionResponse,
)
def create_revision(
    post_id: int,
    variant_id: int,
    data: VariantContent,
    user: CurrentUser,
    db: DbSession,
    _: Csrf,
):
    variant = owned_variant(post_id, variant_id, user, db, lock=True)
    number = (
        db.scalar(
            select(func.max(PlatformVariantRevision.revision_number)).where(
                PlatformVariantRevision.variant_id == variant.id
            )
        )
        or 0
    )
    revision = PlatformVariantRevision(
        variant_id=variant.id,
        revision_number=number + 1,
        origin="seller",
        **data.model_dump(),
    )
    db.add(revision)
    variant.status = "ready"
    variant.error_message = None
    variant.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(revision)
    return revision


@router.get(
    "/posts/{post_id}/variants/{variant_id}/revisions",
    response_model=list[RevisionResponse],
)
def list_revisions(
    post_id: int,
    variant_id: int,
    user: CurrentUser,
    db: DbSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
):
    variant = owned_variant(post_id, variant_id, user, db)
    return db.scalars(
        select(PlatformVariantRevision)
        .where(PlatformVariantRevision.variant_id == variant.id)
        .order_by(PlatformVariantRevision.revision_number.desc())
        .offset(offset)
        .limit(limit)
    ).all()
