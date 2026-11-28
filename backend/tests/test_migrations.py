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
    assert "CREATE TABLE public.products" in upgrade_sql.getvalue()
    assert "CREATE TABLE public.posts" in upgrade_sql.getvalue()
    assert "CREATE TABLE public.post_versions" in upgrade_sql.getvalue()
    assert "CREATE TABLE public.simulations" in upgrade_sql.getvalue()
    assert "CREATE TABLE public.simulation_personas" in upgrade_sql.getvalue()
    assert "CREATE TABLE buyora.persona_adaptations" in upgrade_sql.getvalue()
    assert "ix_persona_adaptations_cache" in upgrade_sql.getvalue()
    assert "ADD COLUMN stage VARCHAR(32) DEFAULT 'queued' NOT NULL" in (
        upgrade_sql.getvalue()
    )
    assert "ADD COLUMN expected_personas INTEGER" in upgrade_sql.getvalue()
    assert "jsonb_array_length(run.inputs -> 'personas')" in upgrade_sql.getvalue()
    assert "ALTER COLUMN expected_personas SET NOT NULL" in upgrade_sql.getvalue()
    assert "REFERENCES public.users (id)" in upgrade_sql.getvalue()
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
    assert include(None, "schema", {})
    assert include("public", "schema", {})
    assert include("users", "table", {"schema_qualified_table_name": "users"})
    assert include("products", "table", {"schema_qualified_table_name": "products"})
    for schema in ("auth", "storage"):
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


def test_post_migration_reuses_existing_tables_and_rejects_partial(monkeypatch):
    import importlib.util
    from unittest.mock import Mock

    import pytest

    path = BACKEND_DIR / "migrations/versions/0005_posts.py"
    spec = importlib.util.spec_from_file_location("migration_posts", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    monkeypatch.setattr(migration.context, "is_offline_mode", lambda: False)
    monkeypatch.setattr(migration.op, "get_bind", lambda: object())
    inspector = Mock()
    monkeypatch.setattr(migration.sa, "inspect", lambda _: inspector)
    create = Mock()
    validate = Mock()
    monkeypatch.setattr(migration, "create_tables", create)
    monkeypatch.setattr(migration, "validate_existing", validate)
    inspector.has_table.side_effect = [True, True]
    migration.upgrade()
    validate.assert_called_once_with(inspector)
    create.assert_not_called()
    inspector.has_table.side_effect = [True, False]
    with pytest.raises(RuntimeError, match="Partial"):
        migration.upgrade()
    create.assert_not_called()
    inspector.has_table.side_effect = [False, False]
    migration.upgrade()
    create.assert_called_once()


def test_auth_migration_accepts_postgresql_reflected_email_index():
    from runpy import run_path

    migration = run_path(str(BACKEND_DIR / "migrations/versions/0002_auth.py"))
    check = migration["is_lower_email_index"]
    assert check({"unique": True, "expressions": ["lower(email)"]})
    assert check({"unique": True, "expressions": ["lower(email::text)"]})
    assert not check({"unique": False, "expressions": ["lower(email::text)"]})
    assert not check({"unique": True, "expressions": ["lower(other::text)"]})
