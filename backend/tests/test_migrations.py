from io import StringIO
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Column, Integer, Table

from app.core.config import BACKEND_DIR
from app.models import Base


def migration_config(output: StringIO) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"), output_buffer=output)
    return config


def test_initial_upgrade_and_downgrade_compile_as_postgresql_sql(monkeypatch) -> None:
    # Offline compilation exercises the real Alembic environment and revision.
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://postgres:p%40ss%25word@localhost/postgres"
    )
    upgrade_sql = StringIO()
    command.upgrade(migration_config(upgrade_sql), "head", sql=True)
    assert "CREATE SCHEMA buyora" in upgrade_sql.getvalue()
    assert "INSERT INTO alembic_version" in upgrade_sql.getvalue()
    assert "p@ss%word" not in upgrade_sql.getvalue()

    downgrade_sql = StringIO()
    command.downgrade(migration_config(downgrade_sql), "0001:base", sql=True)
    assert "DROP SCHEMA buyora" in downgrade_sql.getvalue()
    assert "CASCADE" not in downgrade_sql.getvalue()


def test_autogeneration_excludes_unmanaged_supabase_tables(monkeypatch) -> None:
    from runpy import run_path
    from unittest.mock import patch

    from alembic import context

    config = migration_config(StringIO())
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:test@localhost/postgres")
    with (
        patch.object(context, "config", config, create=True),
        patch.object(context, "is_offline_mode", return_value=True),
        patch.object(context, "configure"),
        patch.object(context, "begin_transaction"),
        patch.object(context, "run_migrations"),
    ):
        environment = run_path(str(Path(BACKEND_DIR / "migrations/env.py")))

    include = environment["include_name"]
    assert include("buyora", "schema", {})
    for schema in (None, "public", "auth", "storage"):
        assert not include(schema, "schema", {})
    assert not include(
        "unmanaged", "table", {"schema_qualified_table_name": "buyora.unmanaged"}
    )
    model_table = Table("managed_example", Base.metadata, Column("id", Integer))
    try:
        assert include(
            "managed_example",
            "table",
            {"schema_qualified_table_name": "buyora.managed_example"},
        )
    finally:
        Base.metadata.remove(model_table)
