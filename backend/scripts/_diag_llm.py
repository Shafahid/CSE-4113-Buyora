"""Temporary diagnostic: prints the raw provider error class/status/message."""

import asyncio
import importlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "true")

from app.core.config import Settings  # noqa: E402
from app.services.llm import model_identity  # noqa: E402


async def main():
    litellm = await asyncio.to_thread(importlib.import_module, "litellm")
    settings = Settings()
    model = model_identity(settings)
    print("model:", model)
    print("api_base:", settings.token_bd_api_url)
    variants = [
        ("with-json-mode", {"response_format": {"type": "json_object"}}),
        ("without-json-mode", {}),
    ]
    for name, extra in variants:
        print("---", name, "---")
        try:
            response = await litellm.acompletion(
                model=model,
                api_base=settings.token_bd_api_url,
                api_key=settings.token_bd_api_key.get_secret_value(),
                messages=[{"role": "user", "content": 'Reply with JSON: {"ok": true}'}],
                temperature=0,
                max_tokens=64,
                timeout=settings.llm_timeout_seconds,
                num_retries=0,
                **extra,
            )
            print("OK:", response.choices[0].message.content)
        except Exception as exc:
            print("TYPE:", type(exc).__name__)
            print("STATUS:", getattr(exc, "status_code", None))
            body = getattr(exc, "body", None)
            message = getattr(exc, "message", None)
            print("BODY:", str(body)[:2000])
            print("MESSAGE:", str(message)[:2000])
            print("STR:", str(exc)[:2000])


asyncio.run(main())
