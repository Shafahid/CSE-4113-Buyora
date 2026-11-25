"""Temporary diagnostic: which check rejects the verdict output."""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "true")

from app.core.config import Settings  # noqa: E402
from app.schemas.execution import BuyerVerdict  # noqa: E402
from app.services.llm import (  # noqa: E402
    SYSTEM_PROMPT,
    provider_completion,
)
from app.services.persona_catalog import profiles  # noqa: E402
from app.services.trust_scoring import DIMENSIONS, strings  # noqa: E402


async def main():
    settings = Settings()
    inputs = {
        "product": {
            "name": "Reusable canvas bag",
            "price": "120.00",
            "currency": "BDT",
            "description": "A reusable canvas bag for everyday shopping.",
            "delivery_info": "Dhaka in 3 days",
            "return_policy": None,
        },
        "post": {
            "headline": "Carry your everyday essentials",
            "body": "Reusable canvas bag. Price BDT 120. Delivery in Dhaka in 3 days.",
            "platform": "Facebook",
        },
        "audience": {"location": "Dhaka"},
        "language": "en",
        "checks": {},
    }
    payload = {
        "product": inputs["product"],
        "post": inputs["post"],
        "audience": inputs["audience"],
        "persona": profiles()[0].model_dump(),
        "output_language": inputs["language"],
        "explicit_information": inputs["checks"],
    }
    content, metadata = await provider_completion(
        settings,
        SYSTEM_PROMPT,
        {"input": payload, "schema": BuyerVerdict.model_json_schema()},
    )
    verdict = BuyerVerdict.model_validate_json(content)
    sources = strings(payload)
    quotes = [
        *verdict.evidence,
        *(quote for driver in verdict.score_drivers for quote in driver.evidence),
    ]
    print("DIMENSIONS:", list(DIMENSIONS))
    print(
        "DRIVER ORDER OK:",
        [d.dimension for d in verdict.score_drivers] == list(DIMENSIONS),
    )
    print("DRIVER ORDER:", [d.dimension for d in verdict.score_drivers])
    for quote in quotes:
        if not quote.strip() or not any(quote in text for text in sources):
            print("UNGROUNDED QUOTE:", repr(quote))
    print("PAYLOAD KEYS SEEN BY strings():")
    print(json.dumps(sorted({t[:70] for t in sources}), ensure_ascii=False)[:3000])


asyncio.run(main())
