"""Add persisted product image analyses.

Revision ID: 0013
Revises: 0012
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "product_image_analyses",
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
        sa.Column(
            "image_id",
            sa.BigInteger(),
            sa.ForeignKey("public.product_images.id", ondelete="SET NULL"),
        ),
        sa.Column("original_image_id", sa.BigInteger(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False, server_default="en"),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
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
            name=sa.schema.conv("image_analyses_status_check"),
        ),
        sa.CheckConstraint(
            "language IN ('en', 'bn')",
            name=sa.schema.conv("image_analyses_language_check"),
        ),
        sa.CheckConstraint(
            "(status = 'completed' AND analysis_result IS NOT NULL) OR "
            "(status <> 'completed' AND analysis_result IS NULL)",
            name=sa.schema.conv("image_analyses_result_check"),
        ),
        schema="public",
    )
    op.create_index(
        "image_analyses_owner_image_idx",
        "product_image_analyses",
        ["seller_id", "product_id", "original_image_id", "created_at", "id"],
        schema="public",
    )
    op.create_index(
        "image_analyses_image_id_idx",
        "product_image_analyses",
        ["image_id"],
        schema="public",
    )
    op.execute("REVOKE ALL ON TABLE public.product_image_analyses FROM PUBLIC")
    op.execute("ALTER TABLE public.product_image_analyses DISABLE ROW LEVEL SECURITY")
    for role in ("anon", "authenticated"):
        op.execute(
            f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles "
            f"WHERE rolname = '{role}') THEN REVOKE ALL ON TABLE "
            f"public.product_image_analyses FROM {role}; END IF; END $$"
        )


def downgrade():
    raise RuntimeError(
        "Image analyses may contain data; downgrade requires manual review"
    )
