"""Durable simulation runs, evaluations and seller-scoped result cache.

Revision ID: 0009
Revises: 0008

New tables live in buyora; unmanaged public.persona_evaluations is untouched.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    # Explicit table order; PostgreSQL DDL is transactional. An existing table
    # fails rather than silently accepting an incompatible schema.
    op.create_table(
        "simulation_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "simulation_id",
            sa.BigInteger(),
            sa.ForeignKey("public.simulations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "seller_id",
            sa.BigInteger(),
            sa.ForeignKey("public.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("inputs", postgresql.JSONB(), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("rules_version", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("lease_token", sa.String(36)),
        sa.Column("report", postgresql.JSONB()),
        sa.UniqueConstraint("seller_id", "request_id"),
        schema="buyora",
    )
    op.create_index(
        "ix_simulation_runs_queue",
        "simulation_runs",
        ["status", "lease_until"],
        schema="buyora",
    )
    op.create_index(
        "ix_simulation_runs_seller_id",
        "simulation_runs",
        ["seller_id"],
        schema="buyora",
    )
    op.create_table(
        "simulation_run_evaluations",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("buyora.simulation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "persona_id",
            sa.BigInteger(),
            sa.ForeignKey("public.simulation_personas.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("profile", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("output", postgresql.JSONB()),
        sa.Column("error_code", sa.String(40)),
        sa.Column("history", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "persona_id"),
        schema="buyora",
    )
    op.create_index(
        "ix_simulation_run_evaluations_run_id",
        "simulation_run_evaluations",
        ["run_id"],
        schema="buyora",
    )
    op.create_table(
        "simulation_cache",
        sa.Column(
            "seller_id",
            sa.BigInteger(),
            sa.ForeignKey("public.users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("fingerprint", sa.String(64), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("buyora.simulation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        schema="buyora",
    )


def downgrade():
    for table in ("simulation_cache", "simulation_run_evaluations", "simulation_runs"):
        op.drop_table(table, schema="buyora")
