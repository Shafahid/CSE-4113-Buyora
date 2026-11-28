import pytest

from app.core.config import Settings


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests must never read credentials from a developer's environment or .env."""
    for name in (
        "DATABASE_URL",
        "MIGRATION_DATABASE_URL",
        "CORS_ORIGINS",
        "SUPABASE_URL",
        "SUPABASE_SECRET_KEY",
        "SUPABASE_STORAGE_BUCKET",
        "TOKEN_BD_API_URL",
        "TOKEN_BD_API_KEY",
        "TOKEN_BD_MODEL",
        "LLM_PROVIDER",
        "LLM_JSON_MODE",
        "LLM_MAX_OUTPUT_TOKENS",
        "LLM_FALLBACK_ENABLED",
        "SIMULATION_MAX_MODEL_CALLS",
        "SIMULATION_TOKEN_BUDGET",
        "SIMULATION_WORKER_ENABLED",
        "PHASE2_AI_REQUESTS_PER_MINUTE",
        "PHASE2_AI_DAILY_TOKEN_BUDGET",
        "PHASE2_AI_MAX_INPUT_TOKENS",
        "PHASE2_AI_MAX_OUTPUT_TOKENS",
        "PHASE2_AI_TIMEOUT_SECONDS",
        "PHASE2_AI_ENABLED",
        "TOKEN_BD_VISION_MODEL",
        "MARKET_EVIDENCE_MAX_AGE_DAYS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    monkeypatch.setenv("SIMULATION_WORKER_ENABLED", "false")
    monkeypatch.setenv("PHASE2_AI_ENABLED", "false")
    monkeypatch.setenv("LITELLM_LOCAL_MODEL_COST_MAP", "true")


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql://postgres:test-password@localhost:5432/postgres",
    )
