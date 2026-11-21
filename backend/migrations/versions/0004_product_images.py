"""Manage public product images while preserving existing rows.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import context, op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def validate_existing(inspector):
    columns = {
        c["name"]: c for c in inspector.get_columns("product_images", schema="public")
    }
    expected = {"id", "product_id", "storage_key", "sort_order", "created_at"}
    if not expected.issubset(columns):
        raise RuntimeError("public.product_images is missing required columns")
    for name in ("id", "product_id"):
        if (
            not isinstance(columns[name]["type"], sa.BigInteger)
            or columns[name]["nullable"]
        ):
            raise RuntimeError(
                f"public.product_images.{name} must be a non-null BIGINT"
            )
    if not columns["id"].get("identity") and not columns["id"].get("default"):
        raise RuntimeError("public.product_images.id must generate IDs")
    if (
        not isinstance(columns["storage_key"]["type"], sa.Text)
        or columns["storage_key"]["nullable"]
    ):
        raise RuntimeError("public.product_images.storage_key must be non-null text")
    if (
        not isinstance(columns["sort_order"]["type"], sa.Integer)
        or columns["sort_order"]["nullable"]
        or not columns["sort_order"].get("default")
    ):
        raise RuntimeError(
            "public.product_images.sort_order must be a non-null integer with a default"
        )
    created = columns["created_at"]
    if (
        not isinstance(created["type"], sa.DateTime)
        or not created["type"].timezone
        or created["nullable"]
        or not created.get("default")
    ):
        raise RuntimeError(
            "public.product_images.created_at must have a timestamp default"
        )
    for name, col in columns.items():
        if (
            name not in expected
            and not col["nullable"]
            and not col.get("default")
            and not col.get("identity")
        ):
            raise RuntimeError(
                f"public.product_images.{name} requires an unsupported value"
            )
    if inspector.get_pk_constraint("product_images", schema="public")[
        "constrained_columns"
    ] != ["id"]:
        raise RuntimeError("public.product_images requires an id primary key")
    fks = inspector.get_foreign_keys("product_images", schema="public")
    if not any(
        f["constrained_columns"] == ["product_id"]
        and f["referred_schema"] in (None, "public")
        and f["referred_table"] == "products"
        and f["referred_columns"] == ["id"]
        and f.get("options", {}).get("ondelete", "").upper() == "CASCADE"
        for f in fks
    ):
        raise RuntimeError(
            "public.product_images requires a cascading product foreign key"
        )
    if not any(
        i.get("column_names", [])[:1] == ["product_id"]
        for i in inspector.get_indexes("product_images", schema="public")
    ):
        raise RuntimeError("public.product_images requires a product_id index")


def create_table():
    op.create_table(
        "product_images",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("public.products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "sort_order >= 0", name=sa.schema.conv("product_images_sort_order_check")
        ),
        sa.CheckConstraint(
            "btrim(storage_key) <> ''",
            name=sa.schema.conv("product_images_storage_key_check"),
        ),
        schema="public",
    )
    op.create_index(
        "product_images_product_id_idx",
        "product_images",
        ["product_id"],
        schema="public",
    )


def upgrade():
    if context.is_offline_mode():
        create_table()
        return
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("product_images", schema="public"):
        validate_existing(inspector)
    else:
        create_table()


def downgrade():
    raise RuntimeError(
        "public.product_images may predate this migration; manual review required"
    )
