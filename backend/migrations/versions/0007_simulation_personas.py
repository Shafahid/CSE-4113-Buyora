"""Manage simulation personas without replacing existing data.

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def validate_existing(inspector):
    columns = {
        c["name"]: c
        for c in inspector.get_columns("simulation_personas", schema="public")
    }
    required = {
        "id",
        "simulation_id",
        "name",
        "characteristics",
        "needs",
        "preferences",
        "budget_sensitivity",
        "is_selected",
        "created_at",
    }
    if not required.issubset(columns):
        raise RuntimeError("public.simulation_personas is missing required columns")
    for name, col in columns.items():
        if (
            name not in required
            and not col["nullable"]
            and not col.get("default")
            and not col.get("identity")
        ):
            raise RuntimeError(
                f"public.simulation_personas.{name} requires an unsupported value"
            )
    for name in ("id", "simulation_id"):
        col = columns[name]
        if not isinstance(col["type"], sa.BigInteger) or col["nullable"]:
            raise RuntimeError(
                f"public.simulation_personas.{name} must be non-null BIGINT"
            )
    if not columns["id"].get("identity") and not columns["id"].get("default"):
        raise RuntimeError("public.simulation_personas.id must generate IDs")
    for name in ("name", "budget_sensitivity"):
        col = columns[name]
        if not isinstance(col["type"], sa.Text) or col["nullable"] != (
            name == "budget_sensitivity"
        ):
            raise RuntimeError(
                f"public.simulation_personas.{name} has an incompatible type"
            )
    characteristics = columns["characteristics"]
    if (
        not isinstance(characteristics["type"], JSONB)
        or characteristics["nullable"]
        or not characteristics.get("default")
    ):
        raise RuntimeError(
            "public.simulation_personas.characteristics must be JSONB with default"
        )
    for name in ("needs", "preferences"):
        col = columns[name]
        if (
            not isinstance(col["type"], ARRAY)
            or not isinstance(col["type"].item_type, sa.Text)
            or col["nullable"]
            or not col.get("default")
        ):
            raise RuntimeError(
                f"public.simulation_personas.{name} must be TEXT[] with default"
            )
    selected = columns["is_selected"]
    if (
        not isinstance(selected["type"], sa.Boolean)
        or selected["nullable"]
        or not selected.get("default")
    ):
        raise RuntimeError(
            "public.simulation_personas.is_selected must be boolean with default"
        )
    created = columns["created_at"]
    if (
        not isinstance(created["type"], sa.DateTime)
        or not created["type"].timezone
        or created["nullable"]
        or not created.get("default")
    ):
        raise RuntimeError(
            "public.simulation_personas.created_at has an incompatible type or default"
        )
    if inspector.get_pk_constraint("simulation_personas", schema="public")[
        "constrained_columns"
    ] != ["id"]:
        raise RuntimeError("public.simulation_personas needs an id primary key")
    fks = inspector.get_foreign_keys("simulation_personas", schema="public")
    if not any(
        f["constrained_columns"] == ["simulation_id"]
        and f["referred_schema"] in (None, "public")
        and f["referred_table"] == "simulations"
        and f["referred_columns"] == ["id"]
        and f.get("options", {}).get("ondelete", "").upper() == "CASCADE"
        for f in fks
    ):
        raise RuntimeError(
            "public.simulation_personas needs a cascading simulation foreign key"
        )
    if not any(
        i.get("column_names", [])[:1] == ["simulation_id"]
        for i in inspector.get_indexes("simulation_personas", schema="public")
    ):
        raise RuntimeError("public.simulation_personas needs a simulation_id index")
    if "simulation_personas_name_check" not in {
        c["name"]
        for c in inspector.get_check_constraints("simulation_personas", schema="public")
    }:
        raise RuntimeError("public.simulation_personas needs a name check")


def create_table():
    op.create_table(
        "simulation_personas",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "simulation_id",
            sa.BigInteger(),
            sa.ForeignKey("public.simulations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "characteristics",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "needs",
            ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "preferences",
            ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("budget_sensitivity", sa.Text()),
        sa.Column(
            "is_selected", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''", name=sa.schema.conv("simulation_personas_name_check")
        ),
        schema="public",
    )
    op.create_index(
        "simulation_personas_simulation_id_idx",
        "simulation_personas",
        ["simulation_id"],
        schema="public",
    )


def upgrade():
    if context.is_offline_mode():
        create_table()
        return
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("simulation_personas", schema="public"):
        validate_existing(inspector)
    else:
        create_table()


def downgrade():
    raise RuntimeError(
        "public.simulation_personas may predate this migration; manual review required"
    )
