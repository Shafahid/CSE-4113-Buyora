"""Behavioral AI contract checks. All providers are mocked; no paid requests."""

import asyncio
import copy
import json
import re
from types import SimpleNamespace

import pytest
from pydantic import SecretStr, ValidationError

from app.core.persona_diversity import duplicate_perspectives
from app.schemas.execution import RunCreate, Verdict
from app.services.llm import ModelFailure, evaluate_persona, provider_completion
from app.services.persona_catalog import profiles
from app.services.persona_engine import contextual_profiles, generate_variants
from app.services.report_insights import (
    objection_groups,
    recommendations,
    revised_caption,
)
from app.services.trust_scoring import (
    DIMENSIONS,
    deterministic_evaluation,
    trust_signals,
)


def inputs(language="en", body="Canvas bag. Price BDT 120."):
    return {
        "language": language,
        "product": {
            "name": "Canvas bag",
            "price": "120.00",
            "currency": "BDT",
            "delivery_info": "Dhaka in 3 days",
            "description": "Cotton canvas",
        },
        "post": {
            "body": body,
            "platform": "Facebook",
            "offer": None,
            "call_to_action": "Inbox to order",
            "hashtags": ["#canvas"],
        },
        "audience": {"location": "Dhaka", "needs": "Daily commute"},
        "personas": [p.model_dump() for p in profiles()],
        "checks": {},
    }


@pytest.mark.parametrize("language", ["en", "bn"])
def test_all_eleven_profiles_are_distinct_contextual_and_editable(language):
    original = inputs(language)
    before = copy.deepcopy(original)
    result = contextual_profiles(original)
    assert len(result) == 11 and not duplicate_perspectives(result)
    assert original == before
    assert {p["id"] for p in result} == {p.id for p in profiles()}
    assert all(
        "Canvas bag" in p["context"] and "Facebook" in p["context"] for p in result
    )
    if language == "bn":
        assert all(re.search(r"[\u0980-\u09ff]", p["need"]) for p in result)
    original["personas"][0]["need"] = "An edited requirement for a cycling commute"
    original["product"]["name"] = "Travel bag"
    changed = contextual_profiles(original)
    assert changed[0]["need"] == original["personas"][0]["need"]
    assert "Travel bag" in changed[0]["context"]
    assert changed[0]["age"] == original["personas"][0]["age"]


def test_duplicate_priorities_rejected_even_with_different_names_and_ids():
    selected = inputs()["personas"][:2]
    selected[1]["need"] = selected[0]["need"].upper() + "!"
    assert duplicate_perspectives(selected)
    with pytest.raises(ValidationError, match="distinct buying priorities"):
        RunCreate(
            request_id="00000000-0000-4000-8000-000000000001",
            post_version_id=1,
            personas=selected,
        )


@pytest.mark.parametrize(
    "body",
    [
        "Price BDT 120. Delivery charge 60. COD available. No returns.",
        "দাম ১২০ টাকা। ডেলিভারি চার্জ ৬০ টাকা। ক্যাশ অন ডেলিভারি। ফেরত নেই।",
        "dam 120 taka. delivery khoroch 60 tk. COD available. ferot nai.",
    ],
)
def test_multilingual_signals_preserve_explicit_negative_policy(body):
    detected = trust_signals(inputs(body=body))
    assert all(
        detected[key]["visible"]
        for key in ("price", "delivery_cost", "payment", "returns")
    )
    assert detected["returns"]["negative"]
    assert not detected["payment"]["negative"]
    assert detected["delivery"]["source"] == "post"


def test_questions_unknown_terms_and_random_numbers_are_not_confirmed_facts():
    data = inputs(body="Model 2026. Delivery charge? Warranty coming soon.")
    data["product"] = {"name": "Bag"}
    detected = trust_signals(data)
    assert not detected["price"]["supplied"]
    assert not detected["delivery_cost"]["supplied"]
    assert not detected["warranty"]["supplied"]


@pytest.mark.parametrize("language", ["en", "bn"])
@pytest.mark.parametrize("count", [2, 5, 10, 11])
def test_fallback_is_stable_bounded_grounded_and_explicit(language, count):
    data = inputs(language)
    for profile in data["personas"][:count]:
        output = deterministic_evaluation(data, profile)
        assert output == deterministic_evaluation(data, profile)
        assert Verdict.model_validate(output)
        assert len(output["scores"]) == 7
        assert all(0 <= score <= 100 for score in output["scores"])
        assert [d["dimension"] for d in output["score_drivers"]] == list(DIMENSIONS)
        assert output["evaluation_source"] == "fallback"
        assert not output["prompt_version"] and output["rules_version"]
        assert "AI" in output["reason"]
        if language == "bn":
            assert all(
                re.search(r"[\u0980-\u09ff]", output[key])
                for key in ("reason", "positive", "comment", "question")
            )
        source = json.dumps(data, ensure_ascii=False)
        assert all(quote in source for quote in output["evidence"])


def test_cod_rejection_reduces_intent_without_turning_it_into_a_benefit():
    data = inputs(body="No COD. Price BDT 120. Inbox to order.")
    profile = next(p for p in data["personas"] if p["id"] == "cod")
    assert deterministic_evaluation(data, profile)["scores"][6] <= 30


def test_recurring_concerns_count_unique_buyers_and_revision_uses_only_facts():
    data = inputs()
    rows = [
        SimpleNamespace(
            status="completed",
            profile=p,
            output={
                "objections": ["Delivery charge?", "Delivery charge?"],
                "evidence": ["Canvas bag"],
            },
        )
        for p in data["personas"][:2]
    ]
    rows.append(
        SimpleNamespace(
            status="failed",
            profile=data["personas"][2],
            output={
                "objections": ["Free delivery?"],
                "evidence": ["Invented free shipping"],
            },
        )
    )
    groups = objection_groups(rows)
    group = next(g for g in groups if g["topic"] == "delivery_cost")
    assert group["frequency"] == 2 and len(group["questions"]) == 1
    recs = recommendations(data, rows)
    rec = next(r for r in recs if r["id"] == "delivery_cost")
    assert rec["frequency"] == 2 and rec["priority"] == "High priority"
    assert "Invented" not in str(recs)
    body = revised_caption(data, ["delivery", "delivery_cost"], recs)
    assert "Dhaka in 3 days" in body
    assert "[confirm verified details before publishing]" in body
    assert "free" not in body.lower() and "discount" not in body.lower()
    assert body.count("Inbox to order") == 1
    with pytest.raises(ValueError, match="saved report"):
        revised_caption(data, ["invented-discount"], recs)


@pytest.mark.parametrize(
    "status,code,retryable",
    [
        (401, "provider_auth", False),
        (429, "rate_limited", True),
        (503, "provider_unavailable", True),
        (400, "provider_configuration", False),
        (405, "provider_configuration", False),
    ],
)
def test_provider_errors_are_safe_and_classified(
    settings, monkeypatch, status, code, retryable
):
    import litellm

    settings.token_bd_api_key = SecretStr("test-secret")
    settings.token_bd_api_url = "https://model.example/v1"
    settings.token_bd_model = "fixture"

    async def fail(**kwargs):
        error = RuntimeError("secret provider response")
        error.status_code = status
        raise error

    monkeypatch.setattr(litellm, "acompletion", fail)
    with pytest.raises(ModelFailure) as caught:
        asyncio.run(provider_completion(settings, "system", {}))
    assert caught.value.code == code and caught.value.retryable == retryable
    assert "secret" not in str(caught.value)
    assert caught.value.metadata["prompt_version"]
    assert caught.value.metadata["http_status"] == status


def test_generated_variants_preserve_identity_and_reject_duplicates_or_wrong_language(
    settings, monkeypatch
):
    async def complete(*args, **kwargs):
        return json.dumps({"profiles": variants}, ensure_ascii=False), {
            "output_tokens": 10
        }

    monkeypatch.setattr("app.services.llm.provider_completion", complete)
    data = inputs()
    variants = [
        {key: p[key] for key in ("id", "role", "need")} for p in data["personas"]
    ]
    result, usage = asyncio.run(generate_variants(settings, data))
    assert [p["id"] for p in result] == [p["id"] for p in data["personas"]]
    assert usage["persona_version"] and usage["output_tokens"] == 10
    data["language"] = "bn"
    with pytest.raises(ModelFailure, match="invalid_persona_output"):
        asyncio.run(generate_variants(settings, data))
    data["language"] = "en"
    variants[1]["need"] = variants[0]["need"]
    with pytest.raises(ModelFailure, match="invalid_persona_output"):
        asyncio.run(generate_variants(settings, data))


@pytest.mark.parametrize(
    "invalid", ["missing_drivers", "invented_evidence", "wrong_language", "bad_json"]
)
def test_evaluator_rejects_incomplete_ungrounded_or_wrong_language_output(
    settings, monkeypatch, invalid
):
    data = inputs("bn" if invalid == "wrong_language" else "en")
    value = deterministic_evaluation(inputs(), data["personas"][0])
    for key in (
        "evaluation_source",
        "fallback_reason",
        "prompt_version",
        "rules_version",
    ):
        value.pop(key)
    if invalid == "missing_drivers":
        value["score_drivers"] = []
    if invalid == "invented_evidence":
        value["score_drivers"][0]["evidence"] = ["Free delivery forever"]

    async def complete(*args, **kwargs):
        return ("{" if invalid == "bad_json" else json.dumps(value)), {
            "output_tokens": 50
        }

    monkeypatch.setattr("app.services.llm.provider_completion", complete)
    with pytest.raises(ModelFailure, match="invalid_output"):
        asyncio.run(evaluate_persona(settings, data, data["personas"][0]))


def test_evaluator_requests_complete_drivers_and_normalizes_their_order(
    settings, monkeypatch
):
    data = inputs()
    value = deterministic_evaluation(data, data["personas"][0])
    for key in (
        "evaluation_source",
        "fallback_reason",
        "prompt_version",
        "rules_version",
    ):
        value.pop(key)
    value["score_drivers"].reverse()

    async def complete(settings, prompt, payload):
        schema = payload["schema"]
        assert "score_drivers" in schema["required"]
        assert schema["properties"]["score_drivers"]["minItems"] == 7
        assert schema["$defs"]["ScoreDriver"]["properties"]["dimension"][
            "enum"
        ] == list(DIMENSIONS)
        return json.dumps(value), {"output_tokens": 50}

    monkeypatch.setattr("app.services.llm.provider_completion", complete)
    result, _ = asyncio.run(evaluate_persona(settings, data, data["personas"][0]))
    assert result["evaluation_source"] == "ai"
    assert [driver["dimension"] for driver in result["score_drivers"]] == list(
        DIMENSIONS
    )

    value["score_drivers"][0]["dimension"] = value["score_drivers"][1]["dimension"]
    with pytest.raises(ModelFailure) as caught:
        asyncio.run(evaluate_persona(settings, data, data["personas"][0]))
    assert caught.value.metadata["validation_check"] == "score_drivers"
