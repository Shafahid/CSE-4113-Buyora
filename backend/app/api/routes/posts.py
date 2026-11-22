from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import MetaData, Table, delete, func, inspect, select

from app.api.routes.auth import check_origin, get_current_user
from app.api.routes.products import owned_product
from app.db.session import DbSession
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

router = APIRouter(tags=["promotional posts"])
CurrentUser = Annotated[User, Depends(get_current_user)]
Csrf = Annotated[None, Depends(check_origin)]


class VersionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    headline: str = Field(min_length=1)
    body: str = Field(min_length=1)
    offer: str | None = None
    call_to_action: str | None = None
    hashtags: list[str] = Field(default_factory=list)
    platform: str = Field(min_length=1)

    @field_validator("headline", "body", "platform", mode="before")
    @classmethod
    def nonblank(cls, value):
        return value.strip() if isinstance(value, str) else value


class VersionResponse(VersionInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    post_id: int
    version_number: int
    created_at: datetime


class PostDetail(BaseModel):
    id: int
    product_id: int
    created_at: datetime
    latest_version: VersionResponse


class PostListItem(BaseModel):
    id: int
    product_id: int
    latest_version_id: int
    version_number: int
    headline: str
    platform: str


def owned_post(post_id: int, user: User, db: DbSession, *, lock: bool = False) -> Post:
    query = (
        select(Post)
        .join(Product, Post.product_id == Product.id)
        .where(
            Post.id == post_id,
            Product.seller_id == user.id,
            Product.deleted_at.is_(None),
        )
    )
    if lock:
        query = query.with_for_update(of=Post)
    post = db.scalar(query)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


def latest_version(post_id: int, db: DbSession) -> PostVersion:
    version = db.scalar(
        select(PostVersion)
        .where(PostVersion.post_id == post_id)
        .order_by(PostVersion.version_number.desc())
        .limit(1)
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Post version not found")
    return version


def detail(post: Post, version: PostVersion) -> PostDetail:
    return PostDetail(
        id=post.id,
        product_id=post.product_id,
        created_at=post.created_at,
        latest_version=VersionResponse.model_validate(version),
    )


@router.post("/products/{product_id}/posts", status_code=201, response_model=PostDetail)
def create_post(
    product_id: int, data: VersionInput, user: CurrentUser, db: DbSession, _: Csrf
):
    product = owned_product(product_id, user, db)
    post = Post(product_id=product.id)
    db.add(post)
    db.flush()
    version = PostVersion(post_id=post.id, version_number=1, **data.model_dump())
    db.add(version)
    db.commit()
    db.refresh(post)
    db.refresh(version)
    return detail(post, version)


@router.get("/products/{product_id}/posts", response_model=list[PostListItem])
def list_posts(product_id: int, user: CurrentUser, db: DbSession):
    owned_product(product_id, user, db)
    latest_number = (
        select(func.max(PostVersion.version_number))
        .where(PostVersion.post_id == Post.id)
        .correlate(Post)
        .scalar_subquery()
    )
    rows = db.execute(
        select(Post, PostVersion)
        .join(
            PostVersion,
            (PostVersion.post_id == Post.id)
            & (PostVersion.version_number == latest_number),
        )
        .where(Post.product_id == product_id)
        .order_by(Post.id.desc())
    ).all()
    return [
        PostListItem(
            id=post.id,
            product_id=post.product_id,
            latest_version_id=version.id,
            version_number=version.version_number,
            headline=version.headline,
            platform=version.platform,
        )
        for post, version in rows
    ]


@router.get("/posts/{post_id}", response_model=PostDetail)
def get_post(post_id: int, user: CurrentUser, db: DbSession):
    post = owned_post(post_id, user, db)
    return detail(post, latest_version(post.id, db))


@router.get("/posts/{post_id}/versions", response_model=list[VersionResponse])
def list_versions(post_id: int, user: CurrentUser, db: DbSession):
    post = owned_post(post_id, user, db)
    return list(
        db.scalars(
            select(PostVersion)
            .where(PostVersion.post_id == post.id)
            .order_by(PostVersion.version_number.desc())
        )
    )


@router.get("/posts/{post_id}/versions/{version_id}", response_model=VersionResponse)
def get_version(post_id: int, version_id: int, user: CurrentUser, db: DbSession):
    post = owned_post(post_id, user, db)
    version = db.scalar(
        select(PostVersion).where(
            PostVersion.post_id == post.id, PostVersion.id == version_id
        )
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Post version not found")
    return version


@router.post(
    "/posts/{post_id}/versions", status_code=201, response_model=VersionResponse
)
def create_version(
    post_id: int, data: VersionInput, user: CurrentUser, db: DbSession, _: Csrf
):
    # PostgreSQL serializes edits for this post before calculating the next number.
    post = owned_post(post_id, user, db, lock=True)
    last_number = (
        db.scalar(
            select(func.max(PostVersion.version_number)).where(
                PostVersion.post_id == post.id
            )
        )
        or 0
    )
    version = PostVersion(
        post_id=post.id, version_number=last_number + 1, **data.model_dump()
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


@router.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int, user: CurrentUser, db: DbSession, _: Csrf):
    post = owned_post(post_id, user, db, lock=True)
    version_ids = select(PostVersion.id).where(PostVersion.post_id == post.id)
    simulation_ids = select(Simulation.id).where(
        Simulation.post_version_id.in_(version_ids)
    )
    persona_ids = select(SimulationPersona.id).where(
        SimulationPersona.simulation_id.in_(simulation_ids)
    )
    run_ids = select(SimulationRun.id).where(
        SimulationRun.simulation_id.in_(simulation_ids)
    )
    db.execute(delete(SimulationCache).where(SimulationCache.run_id.in_(run_ids)))
    db.execute(delete(PersonaEvaluation).where(PersonaEvaluation.run_id.in_(run_ids)))
    db.execute(delete(SimulationRun).where(SimulationRun.id.in_(run_ids)))
    # Some deployments have this unmanaged table; reflect it only if present.
    connection = db.connection()
    schema = None if connection.dialect.name == "sqlite" else "public"
    if inspect(connection).has_table("persona_evaluations", schema=schema):
        evaluations = Table(
            "persona_evaluations", MetaData(), schema=schema, autoload_with=connection
        )
        db.execute(delete(evaluations).where(evaluations.c.persona_id.in_(persona_ids)))
    db.execute(delete(SimulationPersona).where(SimulationPersona.id.in_(persona_ids)))
    db.execute(delete(Simulation).where(Simulation.id.in_(simulation_ids)))
    db.execute(delete(PostVersion).where(PostVersion.post_id == post.id))
    db.delete(post)
    db.commit()
    return Response(status_code=204)
