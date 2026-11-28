"""Durable Stage 2 AI dispatch, heartbeats and processing provenance.

Revision ID: 0018
Revises: 0017
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        op.f("platform_variant_revision_origin_check"),
        "platform_variant_revisions",
        schema="public",
        type_="check",
    )
    op.create_check_constraint(
        op.f("platform_variant_revision_origin_check"),
        "platform_variant_revisions",
        "origin IN ('seller', 'ai', 'fallback')",
        schema="public",
    )
    for table in ("product_image_analyses", "market_analyses", "platform_variants"):
        op.add_column(table, sa.Column("processing_metadata", JSONB()), schema="public")
    op.create_table(
        "ai_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "reservation_id",
            sa.String(36),
            sa.ForeignKey("buyora.ai_request_reservations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "seller_id",
            sa.BigInteger(),
            sa.ForeignKey("public.users.id"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("resource_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("configuration", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("lease_token", sa.String(36)),
        sa.Column("error_code", sa.String(64)),
        sa.Column("usage", JSONB()),
        sa.UniqueConstraint("kind", "resource_id", name="uq_ai_job_resource"),
        schema="buyora",
    )
    op.create_index(
        "ix_ai_jobs_queue",
        "ai_jobs",
        ["status", "lease_until", "created_at"],
        schema="buyora",
    )
    op.create_table(
        "ai_worker_heartbeats",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("configuration", sa.String(64), nullable=False),
        sa.Column("capabilities", JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema="buyora",
    )
    op.create_index(
        "ix_ai_worker_freshness",
        "ai_worker_heartbeats",
        ["updated_at"],
        schema="buyora",
    )
    for table in ("ai_jobs", "ai_worker_heartbeats"):
        op.execute(f"REVOKE ALL ON TABLE buyora.{table} FROM PUBLIC")
        for role in ("anon", "authenticated"):
            op.execute(
                f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles "
                f"WHERE rolname='{role}') THEN REVOKE ALL ON TABLE "
                f"buyora.{table} FROM {role}; END IF; END $$"
            )


def downgrade():
    raise RuntimeError(
        "AI dispatch and provenance may contain data; manual review required"
    )
