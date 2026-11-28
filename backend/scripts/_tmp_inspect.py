import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.core.config import Settings
from app.db.session import create_db_engine

engine = create_db_engine(Settings())
with engine.connect() as c:
    print("alembic_version:", c.execute(text("select * from public.alembic_version")).all())
    rows = c.execute(
        text(
            "select table_schema, table_name from information_schema.tables "
            "where table_name like '%simulation%' or table_name like '%persona%' "
            "order by 1,2"
        )
    ).all()
    print("tables:", rows)
    for row in c.execute(
        text(
            "select column_name, data_type, is_nullable, column_default "
            "from information_schema.columns where table_name='simulation_runs' "
            "and table_schema='buyora' order by ordinal_position"
        )
    ).all():
        print("col:", row)
    print(
        "checks:",
        c.execute(
            text(
                "select conname, pg_get_constraintdef(oid) from pg_constraint "
                "where conrelid='buyora.simulation_runs'::regclass"
            )
        ).all(),
    )
    print(
        "indexes:",
        c.execute(
            text("select indexname, indexdef from pg_indexes where schemaname='buyora' and tablename='simulation_runs'")
        ).all(),
    )
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.core.config import Settings
from app.db.session import create_db_engine

engine = create_db_engine(Settings())
with engine.connect() as c:
    print("alembic_version:", c.execute(text("select * from public.alembic_version")).all())
    for table in (
        "simulation_runs",
        "simulation_run_evaluations",
        "simulation_cache",
        "persona_adaptations",
    ):
        print(f"=== buyora.{table}")
        for row in c.execute(
            text(
                "select column_name, data_type, is_nullable, column_default, character_maximum_length "
                "from information_schema.columns where table_name=:t and table_schema='buyora' "
                "order by ordinal_position"
            ),
            {"t": table},
        ).all():
            print("  ", row)
    print(
        "distinct stages:",
        c.execute(text("select stage, count(*) from buyora.simulation_runs group by 1")).all(),
    )
    print(
        "null expectations:",
        c.execute(
            text(
                "select count(*) from buyora.simulation_runs where expected_personas is null"
            )
        ).scalar(),
    )
    print(
        "evaluation counts:",
        c.execute(
            text(
                "select count(*) from buyora.simulation_run_evaluations"
            )
        ).scalar(),
    )
engine.dispose()

engine.dispose()
