"""One synthetic persona request; no seller data or credentials are printed."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings  # noqa: E402
from app.services.llm import ModelFailure, evaluate_persona  # noqa: E402
from app.services.persona_catalog import profiles  # noqa: E402


async def main():
    settings = Settings()
    if not all(
        (settings.token_bd_api_url, settings.token_bd_api_key, settings.token_bd_model)
    ):
        print("Model settings are incomplete.")
        return 1
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
    try:
        _, usage = await asyncio.wait_for(
            evaluate_persona(settings, inputs, profiles()[0].model_dump()),
            timeout=settings.llm_timeout_seconds + 15,
        )
        print("Configured model returned a valid, grounded seven-score verdict.")
        print("Token usage:", usage)
        return 0
    except ModelFailure as error:
        print("Model check failed:", error.code)
        return 1
    except Exception as error:
        print("Model check failed:", type(error).__name__)
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
