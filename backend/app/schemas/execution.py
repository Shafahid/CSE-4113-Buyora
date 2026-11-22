from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

RULES_VERSION = "buyer-perspectives-v1"
Score = Annotated[int, Field(ge=0, le=100, strict=True)]


class PersonaProfile(BaseModel):
    """Extensible persona input. Its ID identifies a profile, not a real person."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=200)
    age: str = Field(min_length=1, max_length=100)
    location: str = Field(min_length=1, max_length=200)
    need: str = Field(min_length=1, max_length=2000)
    budget: str = Field(min_length=1, max_length=100)
    color: str = Field(min_length=1, max_length=20)
    initials: str = Field(min_length=1, max_length=4)


class RunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    post_version_id: int = Field(gt=0, strict=True)
    language: Literal["en", "bn"] = "en"
    audience: dict[str, str] = Field(default_factory=dict)
    personas: list[PersonaProfile] = Field(min_length=2, max_length=32)
    fresh: bool = False

    @field_validator("audience")
    @classmethod
    def bounded_audience(cls, value):
        allowed = {"location", "age", "interests", "preferences", "budget", "needs"}
        if set(value) - allowed or any(len(v) > 2000 for v in value.values()):
            raise ValueError("Invalid audience settings")
        return value

    @model_validator(mode="after")
    def unique_personas(self):
        if len({p.id for p in self.personas}) != len(self.personas):
            raise ValueError("Persona identities must be unique")
        return self


class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    scores: list[Score] = Field(min_length=7, max_length=7)
    comment: str = Field(min_length=1, max_length=1500)
    reason: str = Field(min_length=1, max_length=2000)
    positive: str = Field(min_length=1, max_length=1500)
    question: str = Field(min_length=1, max_length=1500)
    evidence: list[str] = Field(min_length=1, max_length=12)


class EvaluationProgress(BaseModel):
    id: int
    profile: PersonaProfile
    status: str
    attempts: int
    error_code: str | None
    output: Verdict | None
    can_retry: bool = False


class RunProgress(BaseModel):
    id: str
    simulation_id: int
    status: str
    total: int
    completed: int
    failed: int
    cache_hit: bool = False
    model: str
    created_at: datetime
    started_at: datetime | None
    updated_at: datetime
    evaluations: list[EvaluationProgress]


class RunResponse(RunProgress):
    report: dict | None


class RunPreview(RunCreate):
    # Compare the unsaved editor contents before claiming a cache match.
    post: dict[str, str | list[str] | None]
    product_id: int = Field(gt=0, strict=True)


class PreviewResponse(BaseModel):
    match: bool
    run_id: str | None = None
    status: str | None = None
    completed: int = 0
    total: int = 0
    created_at: datetime | None = None


class BulkRetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID


class SimulationOptions(BaseModel):
    min_personas: int = 2
    max_personas: int
    profiles: list[PersonaProfile]


class RetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evaluation_id: int


class ReportChanges(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revised: str = Field(max_length=30000)
    applied: list[Annotated[str, Field(max_length=100)]] = Field(max_length=100)
