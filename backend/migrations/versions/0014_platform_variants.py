"""Add seller-owned platform variants and immutable revisions.

Revision ID: 0014
Revises: 0013
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "platform_variants",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "source_version_id",
            sa.BigInteger(),
            sa.ForeignKey("public.post_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False, server_default="en"),
        sa.Column("preferences", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False),
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
        sa.CheckConstraint(
            "platform IN ('facebook', 'instagram', 'tiktok', 'whatsapp')",
            name=sa.schema.conv("platform_variants_platform_check"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'ready', 'failed')",
            name=sa.schema.conv("platform_variants_status_check"),
        ),
        sa.CheckConstraint(
            "language IN ('en', 'bn')",
            name=sa.schema.conv("platform_variants_language_check"),
        ),
        schema="public",
    )
    op.create_index(
        "platform_variants_source_idx",
        "platform_variants",
        ["source_version_id", "id"],
        schema="public",
    )
    op.create_table(
        "platform_variant_revisions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "variant_id",
            sa.BigInteger(),
            sa.ForeignKey("public.platform_variants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("offer", sa.Text()),
        sa.Column("call_to_action", sa.Text()),
        sa.Column("hashtags", postgresql.JSONB(), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "variant_id", "revision_number", name="platform_variant_revision_number_key"
        ),
        sa.CheckConstraint(
            "revision_number > 0",
            name=sa.schema.conv("platform_variant_revision_number_check"),
        ),
        sa.CheckConstraint(
            "origin IN ('seller', 'ai')",
            name=sa.schema.conv("platform_variant_revision_origin_check"),
        ),
        schema="public",
    )
    for table in ("platform_variants", "platform_variant_revisions"):
        op.execute(f"REVOKE ALL ON TABLE public.{table} FROM PUBLIC")
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY")
        for role in ("anon", "authenticated"):
            op.execute(
                f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles "
                f"WHERE rolname = '{role}') THEN REVOKE ALL ON TABLE "
                f"public.{table} FROM {role}; END IF; END $$"
            )


def downgrade():
    raise RuntimeError(
        "Platform variants may contain data; downgrade requires manual review"
    )
