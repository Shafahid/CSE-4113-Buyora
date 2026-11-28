import json

import pytest
from pydantic import ValidationError

from app.main import create_app
from scripts.export_phase2_contract import DESTINATION, MODELS


@pytest.mark.parametrize("name,model", MODELS.items())
def test_committed_handover_fixture_matches_current_schema(name, model):
    fixture = json.loads(
        (DESTINATION / f"fixtures/{name}.json").read_text(encoding="utf-8")
    )
    assert fixture["example_only"] is True
    value = model.model_validate(fixture["payload"])
    assert value.model_dump(mode="json") == fixture["payload"]
    schema = json.loads(
        (DESTINATION / f"schemas/{name}.schema.json").read_text(encoding="utf-8")
    )
    assert schema == model.model_json_schema()


def test_unknown_ai_schema_version_is_rejected_and_legacy_default_is_supported():
    model = MODELS["image_insight"]
    fixture = json.loads(
        (DESTINATION / "fixtures/image_insight.json").read_text(encoding="utf-8")
    )
    legacy = fixture["payload"].copy()
    legacy.pop("schema_version")
    assert model.model_validate(legacy).schema_version == "1.0"
    with pytest.raises(ValidationError):
        model.model_validate(legacy | {"schema_version": "2.0"})


def test_committed_openapi_matches_routes_and_documents_limits(settings):
    actual = create_app(settings).openapi()
    saved = json.loads((DESTINATION / "openapi.json").read_text(encoding="utf-8"))
    assert saved == actual
    assert (
        "source_url" in saved["components"]["schemas"]["EvidenceFields"]["properties"]
    )
    assert (
        "429"
        in saved["paths"]["/products/{product_id}/market-analyses"]["post"]["responses"]
    )
