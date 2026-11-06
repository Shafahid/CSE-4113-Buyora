import pytest

from app.core.config import Settings


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests must never read credentials from a developer's environment or .env."""
    for name in ("DATABASE_URL", "MIGRATION_DATABASE_URL", "CORS_ORIGINS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setitem(Settings.model_config, "env_file", None)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql://postgres:test-password@localhost:5432/postgres",
    )
