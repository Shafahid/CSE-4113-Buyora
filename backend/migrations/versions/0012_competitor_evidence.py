"""Create or safely reuse seller-provided competitor evidence.

Revision ID: 0012
Revises: 0011
"""

import sqlalchemy as sa
from alembic import context, op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

TABLE = "competitor_evidence"


def create_table():
    op.create_table(
        TABLE,
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "seller_id",
            sa.BigInteger(),
            sa.ForeignKey("public.users.id"),
            nullable=False,
        ),
        sa.Column("product_id", sa.BigInteger(), sa.ForeignKey("public.products.id")),
        sa.Column("competitor_name", sa.Text(), nullable=False),
        sa.Column("product_name", sa.Text(), nullable=False),
        sa.Column("competitor_description", sa.Text()),
        sa.Column("category", sa.Text()),
        sa.Column("price", sa.Numeric(12, 2)),
        sa.Column("currency", sa.Text()),
        sa.Column("offer", sa.Text()),
        sa.Column("platform", sa.Text()),
        sa.Column("observed_at", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text()),
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
            "btrim(competitor_name) <> ''",
            name=sa.schema.conv("competitor_evidence_name_check"),
        ),
        sa.CheckConstraint(
            "btrim(product_name) <> ''",
            name=sa.schema.conv("competitor_evidence_product_name_check"),
        ),
        sa.CheckConstraint(
            "price IS NULL OR (price >= 0 AND price <> 'NaN'::numeric)",
            name=sa.schema.conv("competitor_evidence_price_check"),
        ),
        sa.CheckConstraint(
            "(price IS NULL AND currency IS NULL) OR "
            "(price IS NOT NULL AND currency IS NOT NULL AND currency ~ '^[A-Z]{3}$')",
            name=sa.schema.conv("competitor_evidence_currency_check"),
        ),
        schema="public",
    )
    op.create_index(
        "competitor_evidence_seller_observed_idx",
        TABLE,
        ["seller_id", "observed_at", "id"],
        schema="public",
    )
    op.create_index(
        "competitor_evidence_product_id_idx", TABLE, ["product_id"], schema="public"
    )
    op.create_index(
        "competitor_evidence_seller_platform_idx",
        TABLE,
        ["seller_id", "platform"],
        schema="public",
    )


def validate_existing(inspector):
    columns = {c["name"]: c for c in inspector.get_columns(TABLE, schema="public")}
    text_names = {
        "competitor_name",
        "product_name",
        "competitor_description",
        "category",
        "currency",
        "offer",
        "platform",
        "notes",
    }
    required = {
        "id",
        "seller_id",
        "competitor_name",
        "product_name",
        "observed_at",
        "created_at",
        "updated_at",
    }
    expected = text_names | {
        "id",
        "seller_id",
        "product_id",
        "price",
        "observed_at",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    if not expected.issubset(columns):
        raise RuntimeError("public.competitor_evidence is missing required columns")
    for name in expected:
        col = columns[name]
        if col["nullable"] != (name not in required):
            raise RuntimeError(
                f"public.competitor_evidence.{name} has incompatible nullability"
            )
        typ = col["type"]
        valid = (
            isinstance(typ, sa.BigInteger)
            if name in {"id", "seller_id", "product_id"}
            else isinstance(typ, sa.Text)
            if name in text_names
            else isinstance(typ, sa.Numeric) and typ.precision == 12 and typ.scale == 2
            if name == "price"
            else isinstance(typ, sa.DateTime) and typ.timezone
            if name in {"created_at", "updated_at", "deleted_at"}
            else isinstance(typ, sa.Date) and not isinstance(typ, sa.DateTime)
        )
        if not valid:
            raise RuntimeError(
                f"public.competitor_evidence.{name} has an incompatible type"
            )
    if not (columns["id"].get("identity") or columns["id"].get("default")) or not all(
        columns[n].get("default") for n in ("created_at", "updated_at")
    ):
        raise RuntimeError("public.competitor_evidence is missing required defaults")
    for name, col in columns.items():
        if (
            name not in expected
            and not col["nullable"]
            and not col.get("default")
            and not col.get("identity")
        ):
            raise RuntimeError(
                f"public.competitor_evidence.{name} requires an unsupported value"
            )
    if inspector.get_pk_constraint(TABLE, schema="public")["constrained_columns"] != [
        "id"
    ]:
        raise RuntimeError("public.competitor_evidence requires id primary key")
    fks = inspector.get_foreign_keys(TABLE, schema="public")
    for col, target in (("seller_id", "users"), ("product_id", "products")):
        if not any(
            f["constrained_columns"] == [col]
            and f["referred_schema"] in (None, "public")
            and f["referred_table"] == target
            and f["referred_columns"] == ["id"]
            and f.get("options", {}).get("ondelete", "NO ACTION").upper()
            in ("NO ACTION", "RESTRICT")
            for f in fks
        ):
            raise RuntimeError(
                f"public.competitor_evidence.{col} requires compatible foreign key"
            )
    indexes = inspector.get_indexes(TABLE, schema="public")
    for prefix in (
        ["seller_id", "observed_at"],
        ["product_id"],
        ["seller_id", "platform"],
    ):
        if not any(i.get("column_names", [])[: len(prefix)] == prefix for i in indexes):
            raise RuntimeError(f"public.competitor_evidence missing index {prefix}")
    checks = {
        c["name"]: c["sqltext"]
        for c in inspector.get_check_constraints(TABLE, schema="public")
    }
    # Require our exact checks and compare normalized PostgreSQL-reflected expressions.
    expected_checks = {
        "competitor_evidence_name_check": ("btrim", "competitor_name"),
        "competitor_evidence_product_name_check": ("btrim", "product_name"),
        "competitor_evidence_price_check": ("price", ">=", "nan"),
        "competitor_evidence_currency_check": (
            "price",
            "currency",
            "^[a-z]{3}$",
            "is null",
            "is not null",
        ),
    }
    for name, tokens in expected_checks.items():
        if name not in checks or not all(
            token in checks[name].lower() for token in tokens
        ):
            raise RuntimeError(
                f"public.competitor_evidence missing compatible constraint {name}"
            )


def upgrade():
    if context.is_offline_mode():
        create_table()
    else:
        inspector = sa.inspect(op.get_bind())
        if inspector.has_table(TABLE, schema="public"):
            validate_existing(inspector)
        else:
            create_table()
    op.execute("REVOKE ALL ON TABLE public.competitor_evidence FROM PUBLIC")
    op.execute("ALTER TABLE public.competitor_evidence DISABLE ROW LEVEL SECURITY")
    for role in ("anon", "authenticated"):
        op.execute(
            f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles "
            f"WHERE rolname = '{role}') THEN REVOKE ALL ON TABLE "
            f"public.competitor_evidence FROM {role}; END IF; END $$"
        )


def downgrade():
    raise RuntimeError(
        "Competitor evidence may contain pre-existing data; manual review required"
    )
