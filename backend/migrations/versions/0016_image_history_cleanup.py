"""Retain immutable image references and queue storage cleanup.

Revision ID: 0016
Revises: 0015
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    # Existing analyses cannot be attributed to an image revision reliably.
    op.add_column(
        "product_image_analyses",
        sa.Column("snapshot_storage_key", sa.Text(), nullable=True),
        schema="public",
    )
    op.create_index(
        "six_product_image_analyses_snapshot_storage_key",
        "product_image_analyses",
        ["snapshot_storage_key"],
        schema="public",
    )
    op.create_table(
        "storage_cleanup_tasks",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("storage_key", sa.Text(), nullable=False, unique=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema="public",
    )
    op.execute("REVOKE ALL ON TABLE public.storage_cleanup_tasks FROM PUBLIC")
    op.execute("ALTER TABLE public.storage_cleanup_tasks DISABLE ROW LEVEL SECURITY")
    for role in ("anon", "authenticated"):
        op.execute(
            f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles "
            f"WHERE rolname = '{role}') THEN REVOKE ALL ON TABLE "
            f"public.storage_cleanup_tasks FROM {role}; END IF; END $$"
        )


def downgrade():
    raise RuntimeError("Image snapshot and cleanup records require manual review")
