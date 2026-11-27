"""Store seller-owned market analysis snapshots.

Revision ID: 0015
Revises: 0014
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "market_analyses",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "seller_id",
            sa.BigInteger(),
            sa.ForeignKey("public.users.id"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("public.products.id"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("language", sa.Text(), nullable=False, server_default="en"),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("analysis_result", postgresql.JSONB()),
        sa.Column("error_message", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name=sa.schema.conv("market_analyses_status_check"),
        ),
        sa.CheckConstraint(
            "language IN ('en', 'bn')",
            name=sa.schema.conv("market_analyses_language_check"),
        ),
        sa.CheckConstraint(
            "(status = 'completed' AND analysis_result IS NOT NULL) OR "
            "(status <> 'completed' AND analysis_result IS NULL)",
            name=sa.schema.conv("market_analyses_result_check"),
        ),
        schema="public",
    )
    op.create_index(
        "market_analyses_owner_product_created_idx",
        "market_analyses",
        ["seller_id", "product_id", "created_at", "id"],
        schema="public",
    )
    op.execute("REVOKE ALL ON TABLE public.market_analyses FROM PUBLIC")
    op.execute("ALTER TABLE public.market_analyses DISABLE ROW LEVEL SECURITY")
    for role in ("anon", "authenticated"):
        op.execute(
            f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles "
            f"WHERE rolname = '{role}') THEN REVOKE ALL ON TABLE "
            f"public.market_analyses FROM {role}; END IF; END $$"
        )


def downgrade():
    raise RuntimeError(
        "Market analyses may contain data; downgrade requires manual review"
    )
