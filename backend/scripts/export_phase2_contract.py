"""Export deterministic, credential-free schemas and example fixtures for handover."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.routes.competitor_evidence import EvidenceResponse  # noqa: E402
from app.api.routes.image_analyses import AnalysisResponse  # noqa: E402
from app.api.routes.market_analyses import MarketResponse  # noqa: E402
from app.api.routes.platform_variants import VariantResponse  # noqa: E402
from app.api.routes.products import ImageCreated, ImageResponse  # noqa: E402
from app.core.config import BACKEND_DIR, Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.schemas.phase2 import OptionalAnalyses  # noqa: E402
from app.services.image_analysis import ImageAnalysisResult  # noqa: E402
from app.services.market_analysis import MarketInput, MarketResult, price_observations  # noqa: E402
from app.services.platform_content import PlatformGenerationResult  # noqa: E402

DESTINATION = BACKEND_DIR.parent / "docs/phase2"
MODELS = {
    "image_insight": ImageAnalysisResult,
    "competitor_evidence": EvidenceResponse,
    "market_input": MarketInput,
    "market_comparison": MarketResult,
    "platform_variant": PlatformGenerationResult,
    "advanced_report": OptionalAnalyses,
    "image_created": ImageCreated,
    "image_reference": ImageResponse,
    "image_analysis_response": AnalysisResponse,
    "market_response": MarketResponse,
    "platform_response": VariantResponse,
}


def fixture_payloads():
    finding = {"assessment": "good", "feedback": "Example: the product is visible."}
    image = {
        key: finding.copy()
        for key in (
            "clarity",
            "lighting",
            "composition",
            "background",
            "text_readability",
            "product_consistency",
        )
    } | {"suggestions": ["Example: use a plain background."]}
    evidence = {
        "id": 1,
        "seller_id": 1,
        "product_id": 1,
        "competitor_name": "Example Store",
        "product_name": "Canvas bag",
        "competitor_description": None,
        "category": "Accessories",
        "price": "125.00",
        "currency": "BDT",
        "offer": None,
        "platform": "facebook",
        "source_url": "https://example.com/listing",
        "source_note": "Seller-entered example; not independently verified",
        "observed_at": "2026-11-28",
        "notes": None,
        "created_at": "2026-11-28T06:00:00Z",
        "updated_at": "2026-11-28T06:00:00Z",
        "deleted_at": None,
    }
    market_input = {
        "product": {
            "id": 1,
            "name": "Canvas bag",
            "category": "Accessories",
            "price": "120.00",
            "currency": "BDT",
            "description": None,
            "features": [],
        },
        "competitors": [
            {
                key: evidence[key]
                for key in (
                    "id",
                    "product_id",
                    "competitor_name",
                    "product_name",
                    "competitor_description",
                    "category",
                    "price",
                    "currency",
                    "offer",
                    "platform",
                    "observed_at",
                    "notes",
                    "source_url",
                    "source_note",
                )
            }
        ],
        "language": "en",
    }
    market = {
        "feature_comparison": "Example only: compare seller-supplied descriptions.",
        "offer_comparison": "No offers were supplied.",
        "competitive_strengths": [],
        "competitive_weaknesses": [],
        "marketing_recommendations": ["Show the bag dimensions."],
        "limitations": ["Example data; no live market research was performed."],
    }
    image = ImageAnalysisResult.model_validate(image).model_dump(mode="json")
    market = MarketResult.model_validate(market).model_dump(mode="json")
    market_input = MarketInput.model_validate(market_input).model_dump(mode="json")
    times = {
        "created_at": "2026-11-28T06:00:00Z",
        "updated_at": "2026-11-28T06:00:00Z",
        "completed_at": "2026-11-28T06:00:00Z",
    }
    return {
        "image_created": {"id": 1, "product_id": 1, "sort_order": 0},
        "image_reference": {
            "id": 1,
            "sort_order": 0,
            "url": "https://example.com/private-example?token=example-only",
            "image_revision": "a" * 64,
        },
        "image_analysis_response": {
            "id": 1,
            "product_id": 1,
            "original_image_id": 1,
            "language": "en",
            "status": "completed",
            "analysis_result": image,
            "error_message": None,
            "processing_available": False,
            "image_revision": "a" * 64,
            "is_current_image": True,
            **times,
        },
        "market_response": {
            "id": 1,
            "product_id": 1,
            "language": "en",
            "status": "completed",
            "input_snapshot": market_input,
            "analysis_result": market,
            "error_message": None,
            "price_observations": price_observations(
                MarketInput.model_validate(market_input)
            ),
            **times,
        },
        "platform_response": {
            "id": 1,
            "source_version_id": 1,
            "platform": "facebook",
            "language": "en",
            "preferences": None,
            "status": "ready",
            "error_message": None,
            "created_at": times["created_at"],
            "updated_at": times["updated_at"],
            "latest_revision": {
                "id": 1,
                "variant_id": 1,
                "revision_number": 1,
                "origin": "seller",
                "created_at": times["created_at"],
                "headline": "Canvas bag",
                "body": "Example seller-authored caption",
            },
        },
        "image_insight": image,
        "competitor_evidence": evidence,
        "market_input": market_input,
        "market_comparison": market,
        "platform_variant": {
            "content": {
                "headline": "Everyday canvas bag",
                "body": "Example caption: BDT 120.",
                "offer": None,
                "call_to_action": "Message us for details",
                "hashtags": ["example"],
            },
            "warnings": ["Example only; no provider was called."],
        },
        # Stage 1 freezes attachments, while Stage 3 owns advanced metrics/PDFs.
        "advanced_report": {
            "image_insights": [
                {
                    "id": 1,
                    "completed_at": "2026-11-28T06:00:00Z",
                    "result": image,
                    "image_revision": "a" * 64,
                }
            ],
            "market_comparisons": [
                {
                    "id": 1,
                    "completed_at": "2026-11-28T06:00:00Z",
                    "result": market,
                    "input_snapshot": market_input,
                }
            ],
        },
    }


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main():
    settings = Settings(
        _env_file=None,
        database_url="postgresql://fixture:fixture@localhost/buyora",
        migration_database_url=None,
        cors_origins=["http://localhost:3000"],
        session_cookie_name="buyora_session",
        session_cookie_secure=False,
        session_cookie_samesite="lax",
    )
    write_json(DESTINATION / "openapi.json", create_app(settings).openapi())
    for name, payload in fixture_payloads().items():
        model = MODELS[name]
        validated = model.model_validate(payload).model_dump(mode="json")
        write_json(
            DESTINATION / f"fixtures/{name}.json",
            {
                "example_only": True,
                "schema": model.__name__,
                "payload": validated,
            },
        )
        write_json(
            DESTINATION / f"schemas/{name}.schema.json", model.model_json_schema()
        )
    print("Exported Phase 2 OpenAPI, versioned schemas and example-only fixtures.")


if __name__ == "__main__":
    main()
