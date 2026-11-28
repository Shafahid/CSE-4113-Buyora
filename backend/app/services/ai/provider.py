"""Bounded Tokens-compatible transport. No retries, raw errors or secret logging."""

import json
from datetime import UTC, datetime
from time import monotonic
from urllib.parse import urlsplit

import httpx

from app.schemas.phase2 import AIMetadata
from app.services.ai import gemini
from app.services.llm import ModelFailure

PROMPT_VERSION = "buyora-optional-ai-v2"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


def configured(settings):
    return bool(
        settings.token_bd_api_url
        and settings.token_bd_api_key
        and settings.token_bd_model
    )


def metadata(source, model, prompt_version, **values):
    allowed = set(AIMetadata.model_fields) - {
        "source",
        "model",
        "prompt_version",
        "evaluated_at",
    }
    return AIMetadata(
        source=source,
        model=model,
        prompt_version=prompt_version,
        evaluated_at=datetime.now(UTC),
        **{key: value for key, value in values.items() if key in allowed},
    )


def failure_usage(error, provenance=None):
    fields = {"input_tokens", "output_tokens", "latency_ms", "input_token_bound"}
    values = provenance.model_dump(include=fields) if provenance is not None else {}
    values.update(
        {
            key: value
            for key, value in getattr(error, "metadata", {}).items()
            if key in fields
        }
    )
    return values


class Gateway:
    def __init__(self, settings, *, transport=None):
        self.settings = settings
        self.transport = transport
        self._vision = (0.0, False)
        self._vision_budget = (0.0, False)

    def model(self, vision=False):
        return (
            (self.settings.token_bd_vision_model or self.settings.token_bd_model)
            if vision
            else self.settings.token_bd_model
        )

    def request(self, path, *, body=None, deadline=None):
        if not configured(self.settings):
            raise ModelFailure("provider_configuration")
        base = self.settings.token_bd_api_url.rstrip("/")
        parsed = urlsplit(base)
        if (
            parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or (
                parsed.scheme != "https"
                and parsed.hostname not in {"localhost", "127.0.0.1"}
            )
        ):
            raise ModelFailure("provider_configuration")
        remaining = (deadline - monotonic()) if deadline else 10
        if remaining <= 0:
            raise ModelFailure("provider_timeout")
        try:
            with httpx.Client(
                timeout=remaining,
                transport=self.transport,
                follow_redirects=False,
            ) as client:
                with client.stream(
                    "POST" if body is not None else "GET",
                    base + path,
                    headers={
                        "Authorization": "Bearer "
                        + self.settings.token_bd_api_key.get_secret_value(),
                        "anthropic-version": "2023-06-01",
                    },
                    json=body,
                ) as response:
                    if response.status_code >= 300:
                        status = response.status_code
                        code = (
                            "provider_auth"
                            if status in {401, 403}
                            else "rate_limited"
                            if status == 429
                            else "provider_unavailable"
                        )
                        raise ModelFailure(code)
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > MAX_RESPONSE_BYTES:
                            raise ModelFailure("provider_response_too_large")
                        if deadline and monotonic() > deadline:
                            raise ModelFailure("provider_timeout")
                        chunks.append(chunk)
                    value = json.loads(b"".join(chunks))
                    if not isinstance(value, dict):
                        raise ModelFailure("invalid_output")
                    return value, response.headers
        except httpx.TimeoutException:
            raise ModelFailure("provider_timeout") from None
        except (httpx.HTTPError, ValueError, TypeError):
            raise ModelFailure("provider_unavailable") from None

    def supports_vision(self):
        """Use explicit capabilities or the documented, live-verified Gemini pin."""
        expiry, supported = self._vision
        if expiry > monotonic():
            return supported
        supported = False
        try:
            catalog, _ = self.request("/models")
            for entry in catalog.get("data", []):
                if entry.get("id") == self.model(vision=True):
                    modalities = entry.get("input_modalities")
                    capability = (entry.get("capabilities") or {}).get("image")
                    if capability is False or (
                        modalities is not None and "image" not in modalities
                    ):
                        supported = False
                    else:
                        supported = (
                            "image" in (modalities or [])
                            or capability is True
                            or self.model(vision=True) == gemini.MODEL
                        )
        except ModelFailure:
            pass
        self._vision = (monotonic() + 300, supported)
        return supported

    def vision_ready(self):
        """Unbilled capability/count probe; never enable based on model name alone."""
        if self._vision_budget[0] > monotonic():
            return self._vision_budget[1]
        ready = False
        if self.supports_vision():
            if self.model(vision=True) == gemini.MODEL:
                # This one pinned model has a documented per-image allocation;
                # every call separately validates the PNG and complete text bound.
                self._vision_budget = (monotonic() + 300, True)
                return True
            import base64
            import io

            from PIL import Image

            output = io.BytesIO()
            Image.new("RGB", (16, 16), "red").save(output, format="PNG")
            try:
                count, headers = self.request(
                    "/messages/count_tokens",
                    body={
                        "model": self.model(vision=True),
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "base64",
                                            "media_type": "image/png",
                                            "data": base64.b64encode(
                                                output.getvalue()
                                            ).decode(),
                                        },
                                    },
                                    {
                                        "type": "text",
                                        "text": "Describe visible colors.",
                                    },
                                ],
                            }
                        ],
                    },
                )
                tokens = count.get("input_tokens")
                ready = (
                    headers.get("x-tokens-estimated", "false").lower() != "true"
                    and type(tokens) is int
                    and tokens > 0
                )
            except ModelFailure:
                pass
        self._vision_budget = (monotonic() + 300, ready)
        return ready

    def complete(self, system, payload, schema, budget, *, prompt_version, image=None):
        started = monotonic()
        deadline = started + budget.timeout_seconds
        selected = self.model(vision=image is not None)
        bound = None
        try:
            user = json.dumps(
                {"input": payload, "output_schema": schema},
                ensure_ascii=False,
                default=str,
            )
            gemini_image = image is not None and selected == gemini.MODEL
            if image is None or gemini_image:
                messages = [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ]
                # A conservative text bound includes the full system/schema/messages,
                # rather than a chars/4 estimate that undercounts Bengali and JSON.
                bound = len(json.dumps(messages, ensure_ascii=False).encode()) + 512
                if gemini_image:
                    if not self.supports_vision():
                        raise ModelFailure("unsupported_vision")
                    messages, bound = gemini.bounded_messages(system, user, image)
                if bound > budget.max_input_tokens:
                    raise ModelFailure("input_token_budget")
                body = {
                    "model": selected,
                    "messages": messages,
                    "max_tokens": budget.max_output_tokens,
                    "temperature": 0.2,
                }
                if self.settings.llm_json_mode:
                    body["response_format"] = {"type": "json_object"}
                response, _ = self.request(
                    "/chat/completions", body=body, deadline=deadline
                )
                choices = response.get("choices") or []
                truncated = not choices or choices[0].get("finish_reason") == "length"
                content = (
                    choices[0].get("message", {}).get("content") if choices else None
                )
                usage = response.get("usage") or {}
                input_tokens, output_tokens = (
                    usage.get("prompt_tokens"),
                    usage.get("completion_tokens"),
                )
            else:
                if not self.supports_vision():
                    raise ModelFailure("unsupported_vision")
                body = {
                    "model": selected,
                    "system": system,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": image,
                                    },
                                },
                                {"type": "text", "text": user},
                            ],
                        }
                    ],
                }
                count, headers = self.request(
                    "/messages/count_tokens", body=body, deadline=deadline
                )
                # Never treat the gateway's flat image-token estimate as a bound.
                if headers.get("x-tokens-estimated", "false").lower() == "true":
                    raise ModelFailure("vision_token_count_unavailable")
                tokens = count.get("input_tokens")
                if type(tokens) is not int or tokens < 1:
                    raise ModelFailure("vision_token_count_unavailable")
                bound = (tokens * 11 + 9) // 10 + 512
                if bound > budget.max_input_tokens:
                    raise ModelFailure("input_token_budget")
                body["max_tokens"] = budget.max_output_tokens
                response, _ = self.request("/messages", body=body, deadline=deadline)
                truncated = response.get("stop_reason") == "max_tokens"
                content = "".join(
                    block.get("text", "")
                    for block in response.get("content", [])
                    if block.get("type") == "text"
                )
                usage = response.get("usage") or {}
                input_tokens, output_tokens = (
                    usage.get("input_tokens"),
                    usage.get("output_tokens"),
                )
            usage_values = {
                "input_tokens": input_tokens
                if type(input_tokens) is int and input_tokens >= 0
                else None,
                "output_tokens": output_tokens
                if type(output_tokens) is int and output_tokens >= 0
                else None,
                "input_token_bound": bound,
                "latency_ms": round((monotonic() - started) * 1000),
            }
            if (usage_values["input_tokens"] or 0) > min(
                budget.max_input_tokens, bound
            ) or (usage_values["output_tokens"] or 0) > budget.max_output_tokens:
                raise ModelFailure("provider_budget_exceeded", metadata=usage_values)
            if truncated:
                raise ModelFailure("invalid_or_truncated_output", metadata=usage_values)
            if not isinstance(content, str):
                raise ModelFailure("invalid_output", metadata=usage_values)
            value = content.strip()
            if value.startswith("```") and "\n" in value:
                value = value.split("\n", 1)[1].rsplit("```", 1)[0]
            try:
                result = json.loads(value)
            except ValueError:
                raise ModelFailure("invalid_output", metadata=usage_values) from None
            return result, metadata(
                "ai",
                selected,
                prompt_version,
                warnings=[gemini.BUDGET_WARNING] if gemini_image else [],
                **usage_values,
            )
        except ModelFailure as error:
            error.metadata = {
                "input_token_bound": bound,
                "latency_ms": round((monotonic() - started) * 1000),
                **error.metadata,
            }
            raise
