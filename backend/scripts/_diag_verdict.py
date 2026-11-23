"""Temporary diagnostic: dumps the raw model JSON for the verdict prompt."""

import asyncio
import importlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "true")

from app.core.config import Settings  # noqa: E402
from app.schemas.execution import BuyerVerdict  # noqa: E402
from app.services.llm import SYSTEM_PROMPT, model_identity  # noqa: E402
from app.services.persona_catalog import profiles  # noqa: E402


async def main():
    litellm = await asyncio.to_thread(importlib.import_module, "litellm")
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
    response = await litellm.acompletion(
        model=model_identity(settings),
        api_base=settings.token_bd_api_url,
        api_key=settings.token_bd_api_key.get_secret_value(),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "input": payload,
                        "schema": BuyerVerdict.model_json_schema(),
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        temperature=0.2,
        max_tokens=settings.llm_max_output_tokens,
        timeout=settings.llm_timeout_seconds,
        num_retries=0,
        response_format={"type": "json_object"},
    )
    choice = response.choices[0]
    print("FINISH_REASON:", getattr(choice, "finish_reason", None))
    print("USAGE:", response.usage)
    content = choice.message.content or ""
    print("LEN:", len(content))
    print("RAW_START")
    print(content)
    print("RAW_END")
    try:
        BuyerVerdict.model_validate_json(content)
        print("VALIDATION: ok")
    except Exception as exc:
        print("VALIDATION: FAILED")
        print(str(exc)[:3000])


asyncio.run(main())
