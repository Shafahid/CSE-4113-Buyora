"""Inspect execution prerequisites without printing configuration or seller data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from alembic.migration import MigrationContext  # noqa: E402
from sqlalchemy import inspect  # noqa: E402

from app.core.config import BACKEND_DIR, Settings  # noqa: E402
from app.db.session import create_db_engine  # noqa: E402


def main():
    settings = Settings()
    print(
        "Model settings present:",
        bool(
            settings.token_bd_api_url
            and settings.token_bd_api_key
            and settings.token_bd_model
        ),
    )
    engine = create_db_engine(settings)
    try:
        with engine.connect() as connection:
            revision = MigrationContext.configure(connection).get_current_revision()
            print("Database revision:", revision)
            inspector = inspect(connection)
            for name in (
                "simulation_runs",
                "simulation_run_evaluations",
                "simulation_cache",
            ):
                print(
                    f"buyora.{name} exists:", inspector.has_table(name, schema="buyora")
                )
        if "--apply" in sys.argv:
            if revision not in {"0007", "0008", "0009"}:
                raise RuntimeError(
                    "Review earlier migrations before applying execution"
                )
            config = Config(str(BACKEND_DIR / "alembic.ini"))
            command.upgrade(config, "0009")
            print("Execution migration applied.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Setup check failed ({type(error).__name__}); no credentials printed.")
        raise SystemExit(1) from None
