from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

BACKEND_DIR = Path(__file__).resolve().parents[2]


def postgres_url(value: SecretStr) -> URL:
    """Accept Supabase connection strings and select the Psycopg 3 driver."""
    try:
        url = make_url(value.get_secret_value())
        valid_port = url.port is None or 1 <= url.port <= 65535
    except (ArgumentError, ValueError):
        raise ValueError("Invalid PostgreSQL connection URL") from None

    if (
        url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}
        or not url.host
        or not url.username
        or not url.database
        or not valid_port
    ):
        raise ValueError("Use a PostgreSQL URL containing a user, host, and database")

    url = url.set(drivername="postgresql+psycopg")
    if "sslmode" not in url.query:
        url = url.update_query_dict({"sslmode": "require"})
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    database_url: SecretStr
    migration_database_url: SecretStr | None = None
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("database_url", "migration_database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None:
            postgres_url(value)
        return value

    @property
    def sqlalchemy_url(self) -> URL:
        return postgres_url(self.database_url)

    @property
    def alembic_url(self) -> URL:
        return postgres_url(self.migration_database_url or self.database_url)
