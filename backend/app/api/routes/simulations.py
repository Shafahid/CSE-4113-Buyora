from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select

from app.api.routes.auth import check_origin, get_current_user
from app.db.session import DbSession
from app.models import Post, PostVersion, Product, Simulation, User

router = APIRouter(tags=["simulation setup"])
CurrentUser = Annotated[User, Depends(get_current_user)]
Csrf = Annotated[None, Depends(check_origin)]


class AgeRange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min: int = Field(ge=0, strict=True)
    max: int | None = Field(default=None, ge=0, strict=True)

    @model_validator(mode="after")
    def validate_bounds(self):
        if "max" in self.model_fields_set and self.max is None:
            raise ValueError("Omit max for an open-ended range")
        if self.max is not None and self.min > self.max:
            raise ValueError("Minimum age cannot exceed maximum age")
        return self


class AudienceSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    location: str | None = None
    age_range: AgeRange | None = None
    interests: list[str] | None = None
    purchasing_preference: (
        Literal["cash_on_delivery", "online_payment", "in_store_pickup"] | None
    ) = None
    budget_sensitivity: Literal["low", "medium", "high"] | None = None
    product_needs: str | None = None

    @model_validator(mode="after")
    def no_nulls(self):
        for name in self.model_fields_set:
            if getattr(self, name) is None:
                raise ValueError(f"Omit {name} when unspecified")
        return self


class SimulationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    post_version_id: int = Field(gt=0, strict=True)
    audience_settings: AudienceSettings = Field(default_factory=AudienceSettings)
    language: Literal["en", "bn"] = "en"


class SimulationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    audience_settings: AudienceSettings | None = None
    language: Literal["en", "bn"] | None = None

    @model_validator(mode="after")
    def no_nulls(self):
        for name in self.model_fields_set:
            if getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class SimulationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    post_version_id: int
    audience_settings: AudienceSettings
    language: Literal["en", "bn"]
    status: str


def owned_simulation(
    simulation_id: int, user: User, db: DbSession, *, lock: bool = False
):
    query = (
        select(Simulation)
        .join(PostVersion, Simulation.post_version_id == PostVersion.id)
        .join(Post, PostVersion.post_id == Post.id)
        .join(Product, Post.product_id == Product.id)
        .where(
            Simulation.id == simulation_id,
            Product.seller_id == user.id,
            Product.deleted_at.is_(None),
        )
    )
    if lock:
        query = query.with_for_update(of=Simulation)
    simulation = db.scalar(query)
    if simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return simulation


@router.post(
    "/simulations",
    status_code=201,
    response_model=SimulationResponse,
    response_model_exclude_none=True,
)
def create_simulation(
    data: SimulationCreate, user: CurrentUser, db: DbSession, _: Csrf
):
    version_id = db.scalar(
        select(PostVersion.id)
        .join(Post, PostVersion.post_id == Post.id)
        .join(Product, Post.product_id == Product.id)
        .where(
            PostVersion.id == data.post_version_id,
            Product.seller_id == user.id,
            Product.deleted_at.is_(None),
        )
    )
    if version_id is None:
        raise HTTPException(status_code=404, detail="Post version not found")
    simulation = Simulation(
        post_version_id=version_id,
        audience_settings=data.audience_settings.model_dump(exclude_none=True),
        language=data.language,
        status="draft",
    )
    db.add(simulation)
    db.commit()
    db.refresh(simulation)
    return simulation


@router.get(
    "/simulations/{simulation_id}",
    response_model=SimulationResponse,
    response_model_exclude_none=True,
)
def get_simulation(simulation_id: int, user: CurrentUser, db: DbSession):
    return owned_simulation(simulation_id, user, db)


@router.patch(
    "/simulations/{simulation_id}",
    response_model=SimulationResponse,
    response_model_exclude_none=True,
)
def update_simulation(
    simulation_id: int,
    data: SimulationUpdate,
    user: CurrentUser,
    db: DbSession,
    _: Csrf,
):
    simulation = owned_simulation(simulation_id, user, db, lock=True)
    if simulation.status != "draft":
        raise HTTPException(status_code=409, detail="Simulation is not a draft")
    if "audience_settings" in data.model_fields_set:
        simulation.audience_settings = data.audience_settings.model_dump(
            exclude_none=True
        )
    if "language" in data.model_fields_set:
        simulation.language = data.language
    db.commit()
    db.refresh(simulation)
    return simulation
