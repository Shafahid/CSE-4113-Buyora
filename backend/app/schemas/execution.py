from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.persona_diversity import duplicate_perspectives

RULES_VERSION = "buyer-perspectives-v2"
PROMPT_VERSION = "buyer-evaluator-v2.1"
PERSONA_VERSION = "contextual-personas-v1"
SIMULATION_MODES = {"quick": 5, "standard": 10, "deep": 20, "extended": 30}
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
    context: str = Field(default="", max_length=2000)
    description_language: Literal["en", "bn"] = "en"


class RunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    post_version_id: int = Field(gt=0, strict=True)
    language: Literal["en", "bn"] = "en"
    audience: dict[str, str] = Field(default_factory=dict)
    personas: list[PersonaProfile] = Field(min_length=2, max_length=30)
    mode: Literal["quick", "standard", "deep", "extended", "custom"] | None = None
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
        if duplicate_perspectives([p.model_dump() for p in self.personas]):
            raise ValueError(
                "Personas need distinct buying priorities, not just different names"
            )
        expected = SIMULATION_MODES.get(self.mode or "")
        if expected is not None and len(self.personas) != expected:
            raise ValueError(
                f"{self.mode.title()} mode requires exactly {expected} personas"
            )
        return self


class ScoreDriver(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dimension: str = Field(min_length=1, max_length=40)
    reason: str = Field(min_length=1, max_length=600)
    evidence: list[str] = Field(default_factory=list, max_length=12)


class BuyerVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    scores: list[Score] = Field(min_length=7, max_length=7)
    comment: str = Field(min_length=1, max_length=1500)
    reason: str = Field(min_length=1, max_length=2000)
    positive: str = Field(min_length=1, max_length=1500)
    question: str = Field(min_length=1, max_length=1500)
    evidence: list[str] = Field(min_length=1, max_length=12)
    objections: list[Annotated[str, Field(min_length=1, max_length=1000)]] = Field(
        default_factory=list, max_length=12
    )
    score_drivers: list[ScoreDriver] = Field(default_factory=list, max_length=7)


class Verdict(BuyerVerdict):
    evaluation_source: Literal["ai", "fallback"] = "ai"
    fallback_reason: str | None = None
    prompt_version: str | None = None
    rules_version: str | None = None


class PersonaAdaptRequest(RunCreate):
    mode: Literal["context", "ai"] = "context"


class PersonaAdaptResponse(BaseModel):
    id: str
    status: str
    profiles: list[PersonaProfile]
    source: Literal["context", "ai", "fallback"]
    cache_hit: bool = False
    error_code: str | None = None
    version: str = PERSONA_VERSION


class Recommendation(BaseModel):
    id: str
    title: str
    detail: str
    priority: str
    addition: str
    evidence: list[str]
    persona_ids: list[str]


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
    stage: str
    expected_personas: int
    total: int
    completed: int
    failed: int
    queued: int
    running: int
    processed: int
    processing_percent: int
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


class SimulationModeOption(BaseModel):
    id: Literal["quick", "standard", "deep", "extended"]
    label: str
    persona_count: Literal[5, 10, 20, 30]


class SimulationOptions(BaseModel):
    min_personas: int = 2
    max_personas: int
    default_mode: Literal["standard"] = "standard"
    modes: list[SimulationModeOption]
    profiles: list[PersonaProfile]


class RetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evaluation_id: int


class RevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    applied: list[Annotated[str, Field(max_length=100)]] = Field(max_length=100)


class ReportChanges(RevisionRequest):
    revised: str = Field(max_length=30000)


class ReportSummary(BaseModel):
    id: str
    title: str
    status: Literal["completed", "partially_failed", "failed"]
    mode: Literal["quick", "standard", "deep", "extended", "custom"]
    persona_count: int
    completed: int
    failed: int
    overall_score: float | None
    dimension_scores: dict[str, float]
    fallback_count: int
    created_at: datetime
    completed_at: datetime | None


class ReportListResponse(BaseModel):
    items: list[ReportSummary]
    total: int
    offset: int
    limit: int


class ReportCompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report_ids: list[UUID] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def distinct_reports(self):
        if self.report_ids[0] == self.report_ids[1]:
            raise ValueError("Choose two different reports")
        return self


class ComparedReport(BaseModel):
    id: str
    title: str
    persona_count: int
    overall_score: float
    created_at: datetime


class DimensionComparison(BaseModel):
    dimension: str
    values: dict[str, float]
    difference: float


class ReportComparison(BaseModel):
    reports: list[ComparedReport]
    dimensions: list[DimensionComparison]
    persona_count_difference: int
    overall_score_difference: float
