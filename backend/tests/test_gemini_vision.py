import base64
import io
import json

import httpx
import pytest
from PIL import Image
from pydantic import SecretStr
from test_stage2_ai import image_bytes, image_result

from app.schemas.phase2 import ExecutionBudget
from app.services.ai import gemini
from app.services.ai.image import VisionImageAnalyzer
from app.services.ai.provider import Gateway
from app.services.image_analysis import ImageAnalysisInput
from app.services.llm import ModelFailure


def gateway(settings, *, entry=None, usage=1500):
    settings.token_bd_api_url = "https://provider.example/v1"
    settings.token_bd_api_key = SecretStr("fixture-only")
    settings.token_bd_model = "text-model"
    settings.token_bd_vision_model = gemini.MODEL
    calls = []

    def respond(request):
        calls.append(request)
        if request.url.path.endswith("/models"):
            return httpx.Response(
                200,
                json={"data": [entry if entry is not None else {"id": gemini.MODEL}]},
            )
        assert request.url.path.endswith("/chat/completions")
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {"content": json.dumps(image_result())},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": usage, "completion_tokens": 400},
            },
        )

    return Gateway(settings, transport=httpx.MockTransport(respond)), calls


def data(budget=None):
    return ImageAnalysisInput(
        product_id=1,
        image_id=1,
        product_details={"name": "Example"},
        image_url="https://private.example/signed-token",
        language="en",
        budget=budget or ExecutionBudget(),
    )


def test_pinned_gemini_uses_bounded_chat_vision_with_unknown_catalog_metadata(settings):
    client, calls = gateway(settings)
    assert client.vision_ready()
    assert len(calls) == 1  # Readiness never performs paid generation.
    result = VisionImageAnalyzer(
        settings, client, image_loader=lambda _: image_bytes()
    ).analyze(data())
    request = json.loads(calls[-1].content)
    assert request["model"] == gemini.MODEL
    assert request["max_tokens"] == data().budget.max_output_tokens
    assert request["messages"][1]["content"][0]["image_url"]["url"].startswith(
        "data:image/png;base64,"
    )
    assert "private.example" not in calls[-1].content.decode()
    assert result.metadata.source == "ai"
    assert result.metadata.input_tokens == 1500
    assert 8192 < result.metadata.input_token_bound < data().budget.max_input_tokens
    assert result.metadata.warnings == [gemini.BUDGET_WARNING]
    assert len(calls) == 2
    assert client.model() == "text-model"


@pytest.mark.parametrize(
    "entry",
    [
        {"id": gemini.MODEL, "capabilities": {"image": False}},
        {"id": gemini.MODEL, "input_modalities": ["text"]},
        {"id": "different-model"},
    ],
)
def test_pin_never_overrides_explicit_denial_or_missing_access(settings, entry):
    client, calls = gateway(settings, entry=entry)
    assert not client.vision_ready()
    assert len(calls) == 1


def test_gemini_bound_rejects_low_budget_before_paid_call(settings):
    client, calls = gateway(settings)
    with pytest.raises(ModelFailure, match="input_token_budget"):
        VisionImageAnalyzer(
            settings, client, image_loader=lambda _: image_bytes()
        ).analyze(data(ExecutionBudget(max_input_tokens=8192)))
    assert len(calls) == 1


def test_gemini_bound_covers_bangla_text_and_rejects_unbounded_images():
    encoded = base64.b64encode(image_bytes()).decode()
    _, english = gemini.bounded_messages("system", "a" * 30, encoded)
    _, bangla = gemini.bounded_messages("system", "ক" * 30, encoded)
    assert bangla > english
    output = io.BytesIO()
    Image.new("RGB", (1025, 1)).save(output, format="PNG")
    for invalid in ("bad base64", base64.b64encode(output.getvalue()).decode()):
        with pytest.raises(ModelFailure, match="invalid_image"):
            gemini.bounded_messages("system", "text", invalid)


def test_provider_exceeding_gemini_bound_fails_without_retry_and_keeps_usage(settings):
    client, calls = gateway(settings, usage=16000)
    with pytest.raises(ModelFailure, match="provider_budget_exceeded") as error:
        VisionImageAnalyzer(
            settings, client, image_loader=lambda _: image_bytes()
        ).analyze(data())
    assert error.value.metadata["input_tokens"] == 16000
    assert len(calls) == 2
