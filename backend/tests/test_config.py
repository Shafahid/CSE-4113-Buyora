from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "postgresql+psycopg"])
def test_supabase_urls_use_psycopg_and_preserve_encoded_password(scheme: str) -> None:
    settings = Settings(
        _env_file=None,
        database_url=f"{scheme}://postgres.ref:p%40ss%25word@db.example.com/postgres",
    )

    assert settings.sqlalchemy_url.drivername == "postgresql+psycopg"
    assert settings.sqlalchemy_url.password == "p@ss%word"
    assert settings.sqlalchemy_url.query["sslmode"] == "require"
    assert "p@ss%word" not in repr(settings)
    assert "p@ss%word" not in repr(settings.sqlalchemy_url)


@pytest.mark.parametrize(
    "url",
    [
        "not-a-url",
        "sqlite:///test.db",
        "mysql://user:password@localhost/db",
        "postgresql://user:password@localhost",
        "postgresql://localhost/db",
        "postgresql://user:password@localhost:99999/db",
    ],
)
def test_invalid_database_configuration_is_rejected_without_exposing_input(url: str):
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, database_url=url)
    assert url not in str(error.value)


def test_missing_database_url_fails_early() -> None:
    with pytest.raises(ValidationError, match="database_url"):
        Settings(_env_file=None)


def test_migration_url_overrides_runtime_url(settings: Settings) -> None:
    assert settings.alembic_url == settings.sqlalchemy_url
    settings = Settings(
        _env_file=None,
        database_url=settings.database_url,
        migration_database_url="postgresql://postgres:secret@direct.example.com/postgres",
    )
    assert settings.alembic_url.host == "direct.example.com"
    assert settings.sqlalchemy_url.host == "localhost"


def test_dotenv_and_environment_precedence(tmp_path: Path, monkeypatch) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        'DATABASE_URL="postgresql://postgres:secret@dotenv.example.com/postgres"\n'
        'CORS_ORIGINS=["https://buyora.example"]\n',
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://postgres:secret@env.example.com/postgres"
    )
    settings = Settings(_env_file=dotenv)
    assert settings.sqlalchemy_url.host == "env.example.com"
    assert settings.cors_origins == ["https://buyora.example"]


def test_local_database_can_explicitly_disable_ssl() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql://postgres:secret@localhost/postgres?sslmode=disable",
    )
    assert settings.sqlalchemy_url.query["sslmode"] == "disable"
