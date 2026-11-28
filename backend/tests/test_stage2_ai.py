import asyncio
import copy
import io
import json
from datetime import date

import httpx
import pytest
from PIL import Image
from pydantic import SecretStr

from app.schemas.phase2 import ExecutionBudget
from app.services.ai.image import VisionImageAnalyzer, prepare_image
from app.services.ai.market import (
    GroundedMarketAnalyzer,
    price_basis,
    quantity,
    verify_grounding,
)
from app.services.ai.platform import BODY_LIMITS, GroundedPlatformGenerator
from app.services.ai.provider import Gateway
from app.services.image_analysis import ImageAnalysisInput
from app.services.llm import ModelFailure, evaluate_persona, unique_sentences
from app.services.market_analysis import MarketInput
from app.services.persona_catalog import profiles
from app.services.persona_engine import contextual_profiles
from app.services.platform_content import PlatformGenerationInput
from app.services.trust_scoring import deterministic_evaluation


def image_bytes():
    output = io.BytesIO()
    Image.new("RGB", (32, 32), "red").save(output, format="PNG")
    return output.getvalue()


def image_result():
    finding = {
        "assessment": "good",
        "severity": "none",
        "feedback": "Keep the product clearly visible.",
        "observation": "The red object is centered on a plain background.",
    }
    return {
        key: finding.copy()
        for key in (
            "clarity",
            "lighting",
            "composition",
            "background",
            "text_readability",
            "product_consistency",
        )
    } | {"suggestions": ["Keep the background plain."]}


def gateway(settings, output, *, estimated=False, status=200, vision=True):
    settings.token_bd_api_url = "https://provider.example/v1"
    settings.token_bd_api_key = SecretStr("test-only-key")
    settings.token_bd_model = "test-model"
    calls = []

    def respond(request):
        calls.append(request)
        path = request.url.path
        if path.endswith("/models"):
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "test-model",
                            "input_modalities": ["text", "image"]
                            if vision
                            else ["text"],
                        }
                    ]
                },
            )
        if path.endswith("/count_tokens"):
            return httpx.Response(
                200,
                json={"input_tokens": 1200},
                headers={"x-tokens-estimated": str(estimated).lower()},
            )
        if status != 200:
            return httpx.Response(status, json={"secret": "private provider message"})
        content = output if isinstance(output, str) else json.dumps(output)
        if path.endswith("/messages"):
            return httpx.Response(
                200,
                json={
                    "content": [{"type": "text", "text": content}],
                    "usage": {"input_tokens": 1200, "output_tokens": 100},
                },
            )
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            },
        )

    return Gateway(settings, transport=httpx.MockTransport(respond)), calls


def market_input(**changes):
    payload = {
        "product": {
            "id": 1,
            "name": "Rice",
            "category": "Food",
            "price": "200.00",
            "currency": "BDT",
            "description": "1 kg",
            "features": [],
        },
        "competitors": [
            {
                "id": 1,
                "product_id": None,
                "competitor_name": "Example",
                "product_name": "Rice",
                "competitor_description": "500 g",
                "category": "Food",
                "price": "120.00",
                "currency": "BDT",
                "offer": None,
                "platform": "facebook",
                "observed_at": "2026-11-20",
                "notes": None,
                "source_url": "https://example.com/rice",
            }
        ],
        "language": "en",
        "comparison_date": "2026-11-28",
    }
    return MarketInput.model_validate(payload | changes)


def platform_input(platform="facebook", language="en"):
    return PlatformGenerationInput(
        source_version_id=1,
        platform=platform,
        language=language,
        preferences=None,
        product={
            "name": "Canvas bag",
            "price": "120.00",
            "currency": "BDT",
            "features": ["Reusable"],
            "description": "Canvas",
        },
        post={
            "headline": "Canvas bag",
            "body": "A reusable bag",
            "offer": None,
            "call_to_action": None,
            "hashtags": ["bag"],
        },
    )


def test_market_compares_units_and_only_ranks_source_grounded_actions(settings):
    data = market_input()
    client, calls = gateway(
        settings, {"action_ids": ["details", "offers"], "evidence_ids": [1]}
    )
    result = GroundedMarketAnalyzer(settings, client).analyze(data)
    assert result.metadata.source == "ai" and result.data_status == "sufficient_data"
    assert "0.2 vs 0.24" in result.competitive_strengths[0]
    assert verify_grounding(data, result, settings)
    assert len(calls) == 1 and result.metadata.input_tokens == 100
    result.competitive_strengths = ["Guaranteed to outsell everyone"]
    assert not verify_grounding(data, result, settings)


@pytest.mark.parametrize(
    "problem", ["stale", "source", "currency", "units", "different_item", "empty"]
)
def test_insufficient_market_data_never_calls_model(settings, problem):
    data = market_input()
    item = data.competitors[0]
    if problem == "stale":
        item.observed_at = date(2020, 1, 1)
    elif problem == "source":
        item.source_url = None
    elif problem == "currency":
        item.currency = "USD"
    elif problem == "units":
        item.competitor_description = "Unknown package"
    elif problem == "different_item":
        item.product_name = "Different rice brand"
    else:
        data.competitors = []
    client, calls = gateway(settings, {})
    result = GroundedMarketAnalyzer(settings, client).analyze(data)
    assert result.data_status == "insufficient_data"
    assert result.metadata.source == "fallback" and not calls
    assert result.competitive_strengths == result.competitive_weaknesses == []


def test_decimal_and_bangla_quantities_are_not_misread():
    assert quantity("0.5 kg") == quantity("৫০০ গ্রাম")
    assert quantity("500 g or 1 kg") is None
    assert price_basis(market_input(), market_input().competitors[0]) is not None


@pytest.mark.parametrize(
    "output", [{"action_ids": ["invent_discount"], "evidence_ids": [99]}, "not JSON"]
)
def test_market_rejects_invented_claims_and_malformed_provider_output(settings, output):
    client, _ = gateway(settings, output)
    result = GroundedMarketAnalyzer(settings, client).analyze(market_input())
    assert result.metadata.source == "fallback"
    assert verify_grounding(market_input(), result, settings)


@pytest.mark.parametrize("language", ["en", "bn"])
def test_four_platforms_are_distinct_and_preserve_commercial_facts(settings, language):
    outputs = []
    for platform in ("facebook", "instagram", "tiktok", "whatsapp"):
        client, _ = gateway(
            settings, {"hook_id": 0, "fact_ids": ["name", "price", "feature_0"]}
        )
        result = GroundedPlatformGenerator(settings, client).generate(
            platform_input(platform, language)
        )
        assert result.metadata.source == "ai"
        assert "BDT 120.00" in result.content.body
        assert result.content.offer is None
        assert "free delivery" not in result.content.body.lower()
        outputs.append(result.content.body)
    assert len(set(outputs)) == 4


def test_platform_provider_failure_or_unrecognized_facts_falls_back(settings):
    client, _ = gateway(settings, {"hook_id": 0, "fact_ids": ["fake_review"]})
    result = GroundedPlatformGenerator(settings, client).generate(platform_input())
    assert result.metadata.source == "fallback"
    assert "fake_review" not in result.content.body


def test_vision_requires_capability_native_count_and_records_usage(settings):
    client, calls = gateway(settings, image_result())
    analyzer = VisionImageAnalyzer(
        settings, client, image_loader=lambda _: image_bytes()
    )
    data = ImageAnalysisInput(
        product_id=1,
        image_id=1,
        product_details={"name": "Red object"},
        image_url="https://private.example/signed",
        language="en",
    )
    result = analyzer.analyze(data)
    assert result.metadata.source == "ai" and result.metadata.input_tokens == 1200
    assert result.clarity.observation
    assert [request.url.path for request in calls] == [
        "/v1/models",
        "/v1/messages/count_tokens",
        "/v1/messages",
    ]
    assert "private.example" not in calls[-1].content.decode()


@pytest.mark.parametrize("problem", ["estimated", "text_only", "bad_output", "claims"])
def test_vision_fails_safely_without_fake_visual_findings(settings, problem):
    value = image_result()
    if problem == "bad_output":
        value = {"unknown": "invalid"}
    if problem == "claims":
        value["suggestions"] = ["This product is authentic"]
    client, calls = gateway(
        settings, value, estimated=problem == "estimated", vision=problem != "text_only"
    )
    analyzer = VisionImageAnalyzer(
        settings, client, image_loader=lambda _: image_bytes()
    )
    data = ImageAnalysisInput(
        product_id=1,
        image_id=1,
        product_details={},
        image_url="https://private.example",
        language="en",
    )
    with pytest.raises(ModelFailure):
        analyzer.analyze(data)
    if problem in {"estimated", "text_only"}:
        assert not any(request.url.path == "/v1/messages" for request in calls)


def test_invalid_images_and_untrusted_references_are_rejected(settings):
    with pytest.raises(ModelFailure):
        prepare_image(b"not an image")
    client, _ = gateway(settings, image_result())
    analyzer = VisionImageAnalyzer(settings, client)
    with pytest.raises(ModelFailure, match="invalid_image_reference"):
        analyzer.load_private_image("http://127.0.0.1/private")


def test_budget_blocks_before_inference_and_provider_auth_has_no_retry(settings):
    client, calls = gateway(settings, {})
    with pytest.raises(ModelFailure, match="input_token_budget"):
        client.complete(
            "system",
            {"payload": "x" * 2000},
            {},
            ExecutionBudget(max_input_tokens=10),
            prompt_version="test",
        )
    assert not calls
    client, calls = gateway(settings, {}, status=401)
    with pytest.raises(ModelFailure, match="provider_auth") as error:
        client.complete("system", {}, {}, ExecutionBudget(), prompt_version="test")
    assert len(calls) == 1 and "private" not in str(error.value)


def test_all_thirty_personas_keep_priorities_without_demographic_inference():
    data = {
        "language": "en",
        "product": {
            "name": "Bag",
            "category": "Accessories",
            "price": "120",
            "currency": "BDT",
        },
        "post": {"platform": "WhatsApp"},
        "audience": {},
        "personas": [profile.model_dump() for profile in profiles()],
    }
    original = copy.deepcopy(data)
    result = contextual_profiles(data)
    assert len(result) == 30
    assert (
        "Accessories" in result[-1]["context"] and "WhatsApp" in result[-1]["context"]
    )
    assert original == data
    assert len({profile["need"] for profile in result}) == 30


def test_banglish_fallback_and_model_language_validation(settings, monkeypatch):
    from test_ai_services import inputs

    data = inputs() | {"writing_style": "banglish"}
    result = deterministic_evaluation(data, data["personas"][0])
    assert "korben" in result["question"]
    value = {
        key: value
        for key, value in result.items()
        if key
        not in {
            "evaluation_source",
            "fallback_reason",
            "prompt_version",
            "rules_version",
            "repeated_language",
        }
    }

    async def complete(*_):
        return json.dumps(value), {"input_tokens": 30, "output_tokens": 20}

    monkeypatch.setattr("app.services.llm.provider_completion", complete)
    assert (
        asyncio.run(evaluate_persona(settings, data, data["personas"][0]))[0][
            "evaluation_source"
        ]
        == "ai"
    )
    assert (
        unique_sentences("Useful detail. Useful detail. Different concern.")
        == "Useful detail. Different concern."
    )


def test_short_platform_preserves_complete_qualifications_and_limits_length(settings):
    data = platform_input("whatsapp")
    data.product["return_policy"] = "Return terms: " + "limited conditions " * 70
    client, _ = gateway(
        settings, {"hook_id": 0, "fact_ids": ["return_policy", "price"]}
    )
    result = GroundedPlatformGenerator(settings, client).generate(data)
    assert len(result.content.body) <= BODY_LIMITS["whatsapp"]
    assert "Return terms" not in result.content.body
    assert "BDT 120.00" in result.content.body
    assert any("omitted" in warning for warning in result.warnings)
