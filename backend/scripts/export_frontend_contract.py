"""Export FastAPI schemas without connecting to a database. Run from backend/."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def ts_type(schema: dict) -> str:
    if "$ref" in schema:
        return f"ApiSchemas[{json.dumps(schema['$ref'].rsplit('/', 1)[-1])}]"
    if "anyOf" in schema or "oneOf" in schema:
        return " | ".join(
            ts_type(item) for item in schema.get("anyOf", schema.get("oneOf"))
        )
    if "allOf" in schema:
        return " & ".join(ts_type(item) for item in schema["allOf"])
    if "enum" in schema:
        return " | ".join(json.dumps(value) for value in schema["enum"])
    if "const" in schema:
        return json.dumps(schema["const"])
    kind = schema.get("type")
    if kind == "array":
        return f"Array<{ts_type(schema.get('items', {}))}>"
    if kind == "object" or "properties" in schema:
        required = schema.get("required", [])
        fields = [
            f"{json.dumps(name)}{'' if name in required else '?'}: {ts_type(value)};"
            for name, value in schema.get("properties", {}).items()
        ]
        extra = schema.get("additionalProperties")
        if extra:
            value_type = ts_type(extra) if isinstance(extra, dict) else "unknown"
            fields.append(f"[key: string]: {value_type};")
        return "{ " + " ".join(fields) + " }" if fields else "Record<string, unknown>"
    return {
        "string": "string",
        "integer": "number",
        "number": "number",
        "boolean": "boolean",
        "null": "null",
    }.get(kind, "unknown")


def main() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql://user:placeholder@localhost/buyora",
        migration_database_url=None,
        cors_origins=["http://localhost:3000"],
        session_cookie_secure=False,
        session_cookie_samesite="lax",
        session_lifetime_seconds=604800,
    )
    schemas = create_app(settings).openapi()["components"]["schemas"]
    target = Path(__file__).resolve().parents[2] / "frontend/src/lib/api-schema.ts"
    lines = [
        "// Generated from FastAPI OpenAPI; do not edit by hand.",
        "// Regenerate from backend: uv run python scripts/export_frontend_contract.py",
        "export type ApiSchemas = {",
        *[
            f"  {json.dumps(name)}: {ts_type(value)};"
            for name, value in schemas.items()
        ],
        "};",
        "",
    ]
    target.write_text("\n".join(lines), encoding="utf-8")
    print("Exported frontend/src/lib/api-schema.ts")


if __name__ == "__main__":
    main()
