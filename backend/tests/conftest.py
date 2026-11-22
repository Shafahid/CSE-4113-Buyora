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
        "SIMULATION_WORKER_ENABLED",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    monkeypatch.setenv("SIMULATION_WORKER_ENABLED", "false")
    monkeypatch.setenv("LITELLM_LOCAL_MODEL_COST_MAP", "true")


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql://postgres:test-password@localhost:5432/postgres",
    )
