"""Inspect database connectivity, worker schema and pending migrations safely."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from alembic.migration import MigrationContext  # noqa: E402
from alembic.script import ScriptDirectory  # noqa: E402
from sqlalchemy import false, inspect, select, text  # noqa: E402

from app.core.config import BACKEND_DIR, Settings  # noqa: E402
from app.db.session import create_db_engine  # noqa: E402
from app.models import (  # noqa: E402
    PersonaAdaptation,
    PersonaEvaluation,
    SimulationCache,
    SimulationRun,
)
from app.services.simulation_worker import worker_failure_hint  # noqa: E402

WORKER_MODELS = (SimulationRun, PersonaEvaluation, SimulationCache, PersonaAdaptation)


def database_revisions(engine):
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        return set(MigrationContext.configure(connection).get_current_heads())


def check_worker_schema(engine):
    ready = True
    with engine.connect() as connection:
        inspector = inspect(connection)
        for model in WORKER_MODELS:
            table = model.__table__
            if not inspector.has_table(table.name, schema=table.schema):
                print(f"Missing worker table: {table.fullname}")
                ready = False
                continue
            actual = {
                column["name"]
                for column in inspector.get_columns(table.name, schema=table.schema)
            }
            missing = set(table.columns.keys()) - actual
            if missing:
                print(
                    f"Missing columns in {table.fullname}: {', '.join(sorted(missing))}"
                )
                ready = False
                continue
            # Check SELECT permissions and mapped columns without reading job data.
            connection.execute(select(model).where(false()))
    return ready


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="Upgrade to repository head"
    )
    args = parser.parse_args(argv)
    engine = None
    try:
        settings = Settings()
        config = Config(str(BACKEND_DIR / "alembic.ini"))
        script = ScriptDirectory.from_config(config)
        heads = set(script.get_heads())
        engine = create_db_engine(settings)
        revisions = database_revisions(engine)
        print("Database connectivity: OK")
        print("Database revisions:", ", ".join(sorted(revisions)) or "unversioned")
        print("Repository heads:", ", ".join(sorted(heads)))
        if args.apply:
            known = {revision.revision for revision in script.walk_revisions()}
            if (
                len(revisions) != 1
                or not revisions <= known
                or revisions & {"0001", "0002", "0003", "0004", "0005", "0006"}
            ):
                print("Review earlier or unknown migrations before applying changes.")
                return 1
            command.upgrade(config, "head")
            # Recheck the runtime URL even when Alembic uses a separate URL.
            revisions = database_revisions(engine)
        ready = check_worker_schema(engine)
        print("Worker schema:", "ready" if ready else "outdated")
        if revisions != heads:
            print("Pending migrations: run uv run alembic upgrade head")
        return 0 if ready and revisions == heads else 1
    except Exception as error:
        print(
            f"Setup check failed ({type(error).__name__}). {worker_failure_hint(error)}"
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
