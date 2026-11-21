from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select

from app.api.routes.simulations import Csrf, CurrentUser, owned_simulation
from app.db.session import DbSession
from app.models import SimulationPersona

router = APIRouter(tags=["simulation personas"])


class PersonaAgeRange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min: int | None = Field(default=None, ge=0, strict=True)
    max: int | None = Field(default=None, ge=0, strict=True)

    @model_validator(mode="after")
    def valid_bounds(self):
        for name in self.model_fields_set:
            if getattr(self, name) is None:
                raise ValueError("Omit an unspecified age bound")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("Minimum age cannot exceed maximum age")
        return self


class Characteristics(BaseModel):
    # Preserve other characteristics produced by future persona workflows.
    model_config = ConfigDict(extra="allow")
    label: str | None = None
    age_range: PersonaAgeRange | None = None


class PersonaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1)
    characteristics: Characteristics = Field(default_factory=Characteristics)
    needs: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)
    budget_sensitivity: Literal["low", "medium", "high"] | None = None
    is_selected: bool = True

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class PersonaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1)
    characteristics: Characteristics | None = None
    needs: list[str] | None = None
    preferences: list[str] | None = None
    budget_sensitivity: Literal["low", "medium", "high"] | None = None
    is_selected: bool | None = None

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def no_null_required_fields(self):
        for name in ("name", "characteristics", "needs", "preferences", "is_selected"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class PersonaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    simulation_id: int
    name: str
    characteristics: dict
    needs: list[str]
    preferences: list[str]
    budget_sensitivity: str | None
    is_selected: bool


def draft_simulation(simulation_id: int, user: CurrentUser, db: DbSession):
    simulation = owned_simulation(simulation_id, user, db, lock=True)
    if simulation.status != "draft":
        raise HTTPException(status_code=409, detail="Simulation is not a draft")
    return simulation


def find_persona(simulation_id: int, persona_id: int, db: DbSession):
    persona = db.scalar(
        select(SimulationPersona).where(
            SimulationPersona.id == persona_id,
            SimulationPersona.simulation_id == simulation_id,
        )
    )
    if persona is None:
        raise HTTPException(status_code=404, detail="Persona not found")
    return persona


@router.get(
    "/simulations/{simulation_id}/personas", response_model=list[PersonaResponse]
)
def list_personas(simulation_id: int, user: CurrentUser, db: DbSession):
    owned_simulation(simulation_id, user, db)
    return list(
        db.scalars(
            select(SimulationPersona)
            .where(SimulationPersona.simulation_id == simulation_id)
            .order_by(SimulationPersona.id)
        )
    )


@router.post(
    "/simulations/{simulation_id}/personas",
    status_code=201,
    response_model=PersonaResponse,
)
def create_persona(
    simulation_id: int, data: PersonaCreate, user: CurrentUser, db: DbSession, _: Csrf
):
    draft_simulation(simulation_id, user, db)
    fields = data.model_dump(exclude={"characteristics"})
    fields["characteristics"] = data.characteristics.model_dump(exclude_unset=True)
    persona = SimulationPersona(simulation_id=simulation_id, **fields)
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return persona


@router.patch(
    "/simulations/{simulation_id}/personas/{persona_id}", response_model=PersonaResponse
)
def update_persona(
    simulation_id: int,
    persona_id: int,
    data: PersonaUpdate,
    user: CurrentUser,
    db: DbSession,
    _: Csrf,
):
    simulation = owned_simulation(simulation_id, user, db, lock=True)
    persona = find_persona(simulation_id, persona_id, db)
    if simulation.status != "draft":
        raise HTTPException(status_code=409, detail="Simulation is not a draft")
    updates = data.model_dump(exclude_unset=True, exclude={"characteristics"})
    if "characteristics" in data.model_fields_set:
        updated = {
            **persona.characteristics,
            **data.characteristics.model_dump(exclude_unset=True),
        }
        updates["characteristics"] = Characteristics.model_validate(updated).model_dump(
            exclude_unset=True
        )
    for name, value in updates.items():
        setattr(persona, name, value)
    db.commit()
    db.refresh(persona)
    return persona


@router.delete("/simulations/{simulation_id}/personas/{persona_id}", status_code=204)
def delete_persona(
    simulation_id: int, persona_id: int, user: CurrentUser, db: DbSession, _: Csrf
):
    simulation = owned_simulation(simulation_id, user, db, lock=True)
    persona = find_persona(simulation_id, persona_id, db)
    if simulation.status != "draft":
        raise HTTPException(status_code=409, detail="Simulation is not a draft")
    db.delete(persona)
    db.commit()
    return Response(status_code=204)
