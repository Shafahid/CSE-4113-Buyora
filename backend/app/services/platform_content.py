"""Provider-independent contracts; no generator or provider is configured.

Generated content must be reviewed against source facts before it is saved as an
AI revision. Schema validation alone cannot establish factual grounding.
"""

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

Platform = Literal["facebook", "instagram", "tiktok", "whatsapp"]


class VariantContent(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    headline: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=10000)
    offer: str | None = Field(default=None, max_length=2000)
    call_to_action: str | None = Field(default=None, max_length=1000)
    hashtags: list[str] = Field(default_factory=list, max_length=50)


class PlatformGenerationInput(BaseModel):
    source_version_id: int
    post: dict
    product: dict
    platform: Platform
    language: Literal["en", "bn"]
    preferences: str | None


class PlatformGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: VariantContent
    warnings: list[str] = Field(default_factory=list, max_length=20)


class PlatformContentGenerator(Protocol):
    def generate(self, data: PlatformGenerationInput) -> PlatformGenerationResult:
        """Return a suggestion for review; never publish or assert fact verification."""
        ...
