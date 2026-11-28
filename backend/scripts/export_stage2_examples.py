"""Export synthetic Stage 2 samples without storage, database or provider calls."""

import sys
from datetime import date, datetime
from pathlib import Path

from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings  # noqa: E402
from app.schemas.execution import PersonaProfile, Verdict  # noqa: E402
from app.schemas.phase2 import AIMetadata  # noqa: E402
from app.services.ai.market import render as render_market  # noqa: E402
from app.services.ai.platform import PlatformPlan  # noqa: E402
from app.services.ai.platform import render as render_platform  # noqa: E402
from app.services.image_analysis import ImageAnalysisResult  # noqa: E402
from app.services.market_analysis import MarketInput, MarketResult  # noqa: E402
from app.services.persona_catalog import profiles  # noqa: E402
from app.services.persona_engine import contextual_profiles  # noqa: E402
from app.services.platform_content import (  # noqa: E402
    PlatformGenerationInput,
    PlatformGenerationResult,
)
from app.services.trust_scoring import deterministic_evaluation  # noqa: E402
from scripts.export_phase2_contract import DESTINATION, fixture_payloads, write_json  # noqa: E402


class Stage2Samples(BaseModel):
    personas: list[PersonaProfile]
    reactions: dict[str, Verdict]
    image_success: ImageAnalysisResult
    image_unavailable: AIMetadata
    market_input: MarketInput
    market_result: MarketResult
    market_insufficient: MarketResult
    platforms: dict[str, PlatformGenerationResult]


def provenance(source="fallback", **values):
    return AIMetadata(
        source=source,
        model="example-only-mocked-model" if source == "ai" else None,
        prompt_version="example-only-v1",
        evaluated_at=datetime.fromisoformat("2026-11-28T06:00:00+00:00"),
        warnings=["Synthetic fixture; tokens and latency were not measured."],
        **values,
    )


def samples():
    settings = Settings(
        _env_file=None,
        database_url="postgresql://fixture:fixture@localhost/buyora",
        market_evidence_max_age_days=90,
    )
    product = {
        "id": 1,
        "name": "Canvas bag",
        "category": "Accessories",
        "price": "120.00",
        "currency": "BDT",
        "description": "1 piece canvas bag",
        "features": ["Reusable"],
    }
    post = {
        "headline": "Canvas bag",
        "body": "A reusable canvas bag. BDT 120.",
        "platform": "Facebook",
        "offer": None,
        "call_to_action": None,
        "hashtags": ["bag"],
    }
    inputs = {
        "product": product,
        "post": post,
        "audience": {"location": "Bangladesh"},
        "language": "en",
        "personas": [p.model_dump() for p in profiles()],
    }
    personas = contextual_profiles(inputs)
    reactions = {}
    for language in ("en", "bn", "banglish"):
        localized = {
            **inputs,
            "language": "bn" if language == "bn" else "en",
            "writing_style": "banglish" if language == "banglish" else "natural",
        }
        profile = contextual_profiles(localized)[0]
        reactions[language] = deterministic_evaluation(
            localized, profile, reason="example_only"
        )
    observations = {
        "clarity": "The red circle has clear visible edges.",
        "lighting": "The synthetic background is uniformly white.",
        "composition": "The red circle is centered in the frame.",
        "background": "No other objects appear on the white background.",
        "text_readability": "There is no visible text to assess.",
        "product_consistency": (
            "A synthetic circle cannot verify a canvas bag description."
        ),
    }
    image = ImageAnalysisResult.model_validate(
        {
            key: {
                "assessment": "uncertain"
                if key == "product_consistency"
                else "not_applicable"
                if key == "text_readability"
                else "good",
                "severity": "uncertain" if key == "product_consistency" else "none",
                "feedback": "Use a photograph of the advertised bag.",
                "observation": observation,
            }
            for key, observation in observations.items()
        }
        | {
            "suggestions": ["Replace the synthetic shape with a clear product photo."],
            "metadata": provenance("ai", failure_code=None),
        }
    )
    data = MarketInput.model_validate(fixture_payloads()["market_input"])
    data.product = type(data.product).model_validate(product)
    data.competitors[0].competitor_description = "1 piece canvas bag"
    data.comparison_date = date(2026, 11, 28)
    market = render_market(data, settings)
    market.metadata = provenance(failure_code="example_only")
    insufficient = render_market(data.model_copy(update={"competitors": []}), settings)
    insufficient.metadata = provenance("unavailable", failure_code="insufficient_data")
    platforms = {}
    for platform in ("facebook", "instagram", "tiktok", "whatsapp"):
        result = render_platform(
            PlatformGenerationInput(
                source_version_id=1,
                product=product,
                post=post,
                platform=platform,
                language="en",
                preferences=None,
            ),
            PlatformPlan(hook_id=0, fact_ids=["name", "price", "feature_0"]),
        )
        result.metadata = provenance(failure_code="example_only")
        platforms[platform] = result
    return Stage2Samples(
        personas=personas,
        reactions=reactions,
        image_success=image,
        image_unavailable=provenance(
            "unavailable", failure_code="vision_token_count_unavailable"
        ),
        market_input=data,
        market_result=market,
        market_insufficient=insufficient,
        platforms=platforms,
    )


def main():
    write_json(
        DESTINATION / "fixtures/stage2_outputs.json",
        {
            "example_only": True,
            "schema": "Stage2Samples",
            "payload": samples().model_dump(mode="json"),
        },
    )
    write_json(
        DESTINATION / "schemas/stage2_outputs.schema.json",
        Stage2Samples.model_json_schema(),
    )
    print("Exported synthetic Stage 2 samples; no provider calls were made.")


if __name__ == "__main__":
    main()
