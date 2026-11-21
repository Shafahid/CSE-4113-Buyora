"""Manage simulation setup tables without replacing existing data.

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def validate_existing(inspector):
    columns = {
        c["name"]: c for c in inspector.get_columns("simulations", schema="public")
    }
    required = {
        "id",
        "post_version_id",
        "language",
        "audience_settings",
        "product_snapshot",
        "evaluation_rules_version",
        "status",
        "analysis",
        "created_at",
        "started_at",
        "completed_at",
    }
    if not required.issubset(columns):
        raise RuntimeError("public.simulations is missing required columns")
    for name, col in columns.items():
        if (
            name not in required
            and not col["nullable"]
            and not col.get("default")
            and not col.get("identity")
        ):
            raise RuntimeError(
                f"public.simulations.{name} requires an unsupported value"
            )
    for name in ("id", "post_version_id"):
        if (
            not isinstance(columns[name]["type"], sa.BigInteger)
            or columns[name]["nullable"]
        ):
            raise RuntimeError(f"public.simulations.{name} must be non-null BIGINT")
    if not columns["id"].get("identity") and not columns["id"].get("default"):
        raise RuntimeError("public.simulations.id must generate IDs")
    for name in ("language", "status", "evaluation_rules_version"):
        col = columns[name]
        if not isinstance(col["type"], sa.Text) or col["nullable"] != (
            name == "evaluation_rules_version"
        ):
            raise RuntimeError(f"public.simulations.{name} has an incompatible type")
    for name in ("audience_settings", "product_snapshot", "analysis"):
        col = columns[name]
        if not isinstance(col["type"], JSONB) or col["nullable"] != (
            name != "audience_settings"
        ):
            raise RuntimeError(f"public.simulations.{name} has an incompatible type")
    for name in ("created_at", "started_at", "completed_at"):
        col = columns[name]
        if (
            not isinstance(col["type"], sa.DateTime)
            or not col["type"].timezone
            or col["nullable"] != (name != "created_at")
        ):
            raise RuntimeError(f"public.simulations.{name} has an incompatible type")
    if any(
        not columns[name].get("default")
        for name in ("language", "status", "audience_settings", "created_at")
    ):
        raise RuntimeError("public.simulations is missing required defaults")
    if inspector.get_pk_constraint("simulations", schema="public")[
        "constrained_columns"
    ] != ["id"]:
        raise RuntimeError("public.simulations needs an id primary key")
    fks = inspector.get_foreign_keys("simulations", schema="public")
    if not any(
        f["constrained_columns"] == ["post_version_id"]
        and f["referred_schema"] in (None, "public")
        and f["referred_table"] == "post_versions"
        and f["referred_columns"] == ["id"]
        for f in fks
    ):
        raise RuntimeError("public.simulations needs a post_versions foreign key")
    if not any(
        i.get("column_names", [])[:1] == ["post_version_id"]
        for i in inspector.get_indexes("simulations", schema="public")
    ):
        raise RuntimeError("public.simulations needs a post_version_id index")
    checks = {
        c["name"]
        for c in inspector.get_check_constraints("simulations", schema="public")
    }
    if not {"simulations_language_check", "simulations_status_check"}.issubset(checks):
        raise RuntimeError("public.simulations is missing required checks")


def create_table():
    op.create_table(
        "simulations",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "post_version_id",
            sa.BigInteger(),
            sa.ForeignKey("public.post_versions.id"),
            nullable=False,
        ),
        sa.Column("language", sa.Text(), nullable=False, server_default="en"),
        sa.Column(
            "audience_settings",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("product_snapshot", JSONB()),
        sa.Column("evaluation_rules_version", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("analysis", JSONB()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "language IN ('en', 'bn')",
            name=sa.schema.conv("simulations_language_check"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'queued', 'running', 'completed', "
            "'partially_failed', 'failed')",
            name=sa.schema.conv("simulations_status_check"),
        ),
        schema="public",
    )
    op.create_index(
        "simulations_post_version_id_idx",
        "simulations",
        ["post_version_id"],
        schema="public",
    )


def upgrade():
    if context.is_offline_mode():
        create_table()
        return
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("simulations", schema="public"):
        validate_existing(inspector)
    else:
        create_table()


def downgrade():
    raise RuntimeError(
        "public.simulations may predate this migration; manual review required"
    )
