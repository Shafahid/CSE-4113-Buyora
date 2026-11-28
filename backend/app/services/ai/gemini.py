"""Pinned, live-verified Gemini vision policy; never infer from a model prefix.

Capability: https://tokens.bd/models/google/gemini-3.8-flash
Image allocation: https://ai.google.dev/gemini-api/docs/media-resolution
Verified 2026-11-28; see docs/phase2/verification/gemini_vision_live_check.json.
Google documents 1120 image tokens at default/high and 2240 at ultra high for
Gemini 3. Reserve 8192 for ONE bounded PNG plus 1024 for request framing. Count
all prompt/schema text conservatively as UTF-8 bytes. This is a conservative
allowance, not the gateway's flat image estimate or a currency-charge guarantee.
"""

import base64
import binascii
import io
import json

from PIL import Image

from app.services.llm import ModelFailure

MODEL = "google/gemini-3.8-flash"
IMAGE_TOKEN_ALLOWANCE = 8192
FRAMING_TOKEN_ALLOWANCE = 1024
BUDGET_WARNING = (
    "Conservative Gemini input bound: full UTF-8 prompt plus 8192 image and "
    "1024 framing tokens; not a native token count."
)


def bounded_messages(system, user, encoded):
    """Return a single-image chat body and a bound without counting base64 as text."""
    if not isinstance(encoded, str) or len(encoded) > 7 * 1024 * 1024:
        raise ModelFailure("invalid_image")
    try:
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > 5 * 1024 * 1024:
            raise ValueError("Too large")
        with Image.open(io.BytesIO(raw), formats=["PNG"]) as image:
            if (
                max(image.size) > 1024
                or min(image.size) < 1
                or getattr(image, "is_animated", False)
            ):
                raise ValueError("Unbounded image")
            image.verify()
    except (ValueError, OSError, binascii.Error, Image.DecompressionBombError):
        raise ModelFailure("invalid_image") from None
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/png;base64,", "detail": "low"},
                },
                {"type": "text", "text": user},
            ],
        },
    ]
    bound = (
        len(json.dumps(messages, ensure_ascii=False).encode())
        + IMAGE_TOKEN_ALLOWANCE
        + FRAMING_TOKEN_ALLOWANCE
    )
    messages[1]["content"][0]["image_url"]["url"] += encoded
    return messages, bound
