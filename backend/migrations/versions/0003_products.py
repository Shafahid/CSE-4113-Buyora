"""Manage public products without replacing an existing table.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def validate_existing(inspector):
    columns = {
        col["name"]: col for col in inspector.get_columns("products", schema="public")
    }
    names = {
        "id",
        "seller_id",
        "name",
        "price",
        "currency",
        "category",
        "description",
        "features",
        "warranty",
        "delivery_info",
        "return_policy",
        "status",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    if not names.issubset(columns):
        raise RuntimeError("public.products is missing required columns")
    for name in ("id", "seller_id"):
        if (
            not isinstance(columns[name]["type"], sa.BigInteger)
            or columns[name]["nullable"]
        ):
            raise RuntimeError(f"public.products.{name} must be a non-null BIGINT")
    identity = columns["id"]
    if not identity.get("identity") and not identity.get("default"):
        raise RuntimeError("public.products.id must generate IDs")
    for name in ("name", "currency", "category", "status"):
        if not isinstance(columns[name]["type"], sa.Text) or columns[name]["nullable"]:
            raise RuntimeError(f"public.products.{name} must be non-null text")
    for name in ("description", "warranty", "delivery_info", "return_policy"):
        if (
            not isinstance(columns[name]["type"], sa.Text)
            or not columns[name]["nullable"]
        ):
            raise RuntimeError(f"public.products.{name} must be nullable text")
    price = columns["price"]
    if (
        not isinstance(price["type"], sa.Numeric)
        or price["type"].precision != 12
        or price["type"].scale != 2
        or price["nullable"]
    ):
        raise RuntimeError("public.products.price must be non-null NUMERIC(12,2)")
    features = columns["features"]
    if (
        not isinstance(features["type"], postgresql.ARRAY)
        or not isinstance(features["type"].item_type, sa.Text)
        or features["nullable"]
    ):
        raise RuntimeError("public.products.features must be non-null TEXT[]")
    for name in ("created_at", "updated_at", "deleted_at"):
        column = columns[name]
        if (
            not isinstance(column["type"], sa.DateTime)
            or not column["type"].timezone
            or column["nullable"] != (name == "deleted_at")
        ):
            raise RuntimeError(f"public.products.{name} has an incompatible type")
    if any(
        not columns[n].get("default")
        for n in ("currency", "features", "status", "created_at", "updated_at")
    ):
        raise RuntimeError("public.products is missing required defaults")
    for name, col in columns.items():
        if (
            name not in names
            and not col["nullable"]
            and not col.get("default")
            and not col.get("identity")
        ):
            raise RuntimeError(f"public.products.{name} requires an unsupported value")
    if inspector.get_pk_constraint("products", schema="public")[
        "constrained_columns"
    ] != ["id"]:
        raise RuntimeError("public.products requires an id primary key")
    fks = inspector.get_foreign_keys("products", schema="public")
    if not any(
        f["constrained_columns"] == ["seller_id"]
        and f["referred_schema"] in (None, "public")
        and f["referred_table"] == "users"
        and f["referred_columns"] == ["id"]
        for f in fks
    ):
        raise RuntimeError("public.products.seller_id must reference public.users.id")
    if not any(
        i.get("column_names", [])[:1] == ["seller_id"]
        for i in inspector.get_indexes("products", schema="public")
    ):
        raise RuntimeError("public.products needs an index on seller_id")


def create_table():
    op.create_table(
        "products",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "seller_id",
            sa.BigInteger(),
            sa.ForeignKey("public.users.id"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False, server_default="BDT"),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column(
            "features",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("warranty", sa.Text()),
        sa.Column("delivery_info", sa.Text()),
        sa.Column("return_policy", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "btrim(name) <> ''", name=sa.schema.conv("products_name_check")
        ),
        sa.CheckConstraint(
            "btrim(category) <> ''", name=sa.schema.conv("products_category_check")
        ),
        sa.CheckConstraint(
            "price >= 0 AND price <> 'NaN'::numeric",
            name=sa.schema.conv("products_price_check"),
        ),
        sa.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'", name=sa.schema.conv("products_currency_check")
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name=sa.schema.conv("products_status_check"),
        ),
        schema="public",
    )
    op.create_index(
        "products_seller_id_idx", "products", ["seller_id"], schema="public"
    )


def upgrade():
    if context.is_offline_mode():
        create_table()
        return
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("products", schema="public"):
        validate_existing(inspector)
    else:
        create_table()


def downgrade():
    raise RuntimeError(
        "public.products may predate this migration; manual review required"
    )
