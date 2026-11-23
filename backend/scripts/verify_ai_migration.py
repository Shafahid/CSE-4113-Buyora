"""Verify 0010 on the configured PostgreSQL database; never print credentials.

Pass --apply to apply only 0009 -> 0010 after checking the current revision.
No customer rows are created, modified, or removed.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import create_engine, inspect, text  # noqa: E402

from app.core.config import BACKEND_DIR, Settings  # noqa: E402
from app.models import PersonaAdaptation  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    engine = None
    try:
        engine = create_engine(
            Settings().alembic_url,
            hide_parameters=True,
            connect_args={"connect_timeout": 10, "prepare_threshold": None},
        )
        with engine.connect() as connection:
            revisions = set(
                connection.scalars(text("SELECT version_num FROM alembic_version"))
            )
        if revisions not in ({"0009"}, {"0010"}):
            print("Unexpected migration revision; no changes made.")
            return 1
        if revisions == {"0009"}:
            if not args.apply:
                print("Database is at 0009; 0010 has not been applied.")
                return 1
            command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "0010")
        with engine.connect() as connection:
            inspector = inspect(connection)
            actual = {
                c["name"]
                for c in inspector.get_columns("persona_adaptations", schema="buyora")
            }
            expected = set(PersonaAdaptation.__table__.columns.keys())
            assert actual == expected, "column mismatch"
            indexes = inspector.get_indexes("persona_adaptations", schema="buyora")
            assert any(
                i["column_names"] == ["seller_id", "fingerprint"] for i in indexes
            )
            constraints = inspector.get_unique_constraints(
                "persona_adaptations", schema="buyora"
            )
            assert any(
                c["column_names"] == ["seller_id", "request_id"] for c in constraints
            )
            fks = inspector.get_foreign_keys("persona_adaptations", schema="buyora")
            assert {fk["referred_table"] for fk in fks} == {"users", "products"}
            assert set(
                connection.scalars(text("SELECT version_num FROM alembic_version"))
            ) == {"0010"}
        print(
            "Verified revision 0010, columns, cache index, request uniqueness "
            "and ownership foreign keys."
        )
        return 0
    except Exception as error:
        # Driver messages can contain hostnames, credentials or connection URLs.
        print(
            f"Migration verification failed ({type(error).__name__}); "
            "details withheld to protect connection settings."
        )
        return 1
    finally:
        if engine:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
