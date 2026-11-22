from pathlib import Path
from typing import Literal

from pydantic import Field, PositiveInt, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

BACKEND_DIR = Path(__file__).resolve().parents[2]


def postgres_url(value: SecretStr) -> URL:
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
    supabase_url: str | None = None
    supabase_secret_key: SecretStr | None = None
    supabase_storage_bucket: str | None = None
    session_cookie_name: str = "buyora_session"
    session_cookie_secure: bool = False
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    session_lifetime_seconds: PositiveInt = 604800
    token_bd_api_url: str | None = None
    token_bd_api_key: SecretStr | None = None
    token_bd_model: str | None = None
    llm_provider: str = "openai"
    llm_json_mode: bool = True
    llm_timeout_seconds: int = Field(default=45, ge=5, le=180)
    llm_max_output_tokens: int = Field(default=4096, ge=256, le=16384)
    llm_max_attempts: int = Field(default=2, ge=1, le=3)
    simulation_max_personas: int = Field(default=12, ge=2, le=32)
    simulation_concurrency: int = Field(default=3, ge=1, le=8)
    simulation_worker_enabled: bool = True

    @model_validator(mode="after")
    def validate_cookie(self):
        if self.session_cookie_samesite == "none" and not self.session_cookie_secure:
            raise ValueError("SameSite=None requires a secure cookie")
        return self

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
