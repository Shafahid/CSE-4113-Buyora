"""Versioned Stage 1 contracts; defaults keep historical JSON readable."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExecutionBudget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    max_input_tokens: int = Field(default=16384, ge=1)
    max_output_tokens: int = Field(default=4096, ge=1)
    max_attempts: Literal[1] = 1
    timeout_seconds: int = Field(default=90, ge=1, le=180)


class AIMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: Literal["ai", "fallback", "unavailable"]
    model: str | None = None
    prompt_version: str
    failure_code: str | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    latency_ms: int = Field(default=0, ge=0)
    input_token_bound: int | None = Field(default=None, ge=0)
    evaluated_at: datetime
    warnings: list[str] = Field(default_factory=list, max_length=20)


class AnalysisAttachment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    id: int = Field(gt=0)
    completed_at: datetime
    # Frozen validated analysis output, including provenance when applicable.
    result: dict
    input_snapshot: dict | None = None
    image_revision: str | None = None


class OptionalAnalyses(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    image_insights: list[AnalysisAttachment] = Field(
        default_factory=list, max_length=10
    )
    market_comparisons: list[AnalysisAttachment] = Field(
        default_factory=list, max_length=5
    )
