"""Manage seller-written posts and versions without replacing existing data.

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def validate_existing(inspector):
    expected = {
        "posts": {"id", "product_id", "created_at"},
        "post_versions": {
            "id",
            "post_id",
            "version_number",
            "headline",
            "body",
            "offer",
            "call_to_action",
            "hashtags",
            "platform",
            "created_at",
        },
    }
    cols = {}
    for table, names in expected.items():
        columns = {c["name"]: c for c in inspector.get_columns(table, schema="public")}
        cols[table] = columns
        if not names.issubset(columns):
            raise RuntimeError(f"public.{table} is missing required columns")
        for name, col in columns.items():
            if (
                name not in names
                and not col["nullable"]
                and not col.get("default")
                and not col.get("identity")
            ):
                raise RuntimeError(
                    f"public.{table}.{name} requires an unsupported value"
                )
        for name in ("id", "product_id" if table == "posts" else "post_id"):
            if (
                not isinstance(columns[name]["type"], sa.BigInteger)
                or columns[name]["nullable"]
            ):
                raise RuntimeError(f"public.{table}.{name} must be non-null BIGINT")
        if not columns["id"].get("identity") and not columns["id"].get("default"):
            raise RuntimeError(f"public.{table}.id must generate IDs")
        created = columns["created_at"]
        if (
            not isinstance(created["type"], sa.DateTime)
            or not created["type"].timezone
            or created["nullable"]
            or not created.get("default")
        ):
            raise RuntimeError(
                f"public.{table}.created_at has an incompatible type or default"
            )
        if inspector.get_pk_constraint(table, schema="public")[
            "constrained_columns"
        ] != ["id"]:
            raise RuntimeError(f"public.{table} needs an id primary key")
    versions = cols["post_versions"]
    for name in ("headline", "body", "platform", "offer", "call_to_action"):
        c = versions[name]
        if not isinstance(c["type"], sa.Text) or c["nullable"] != (
            name in ("offer", "call_to_action")
        ):
            raise RuntimeError(f"public.post_versions.{name} has an incompatible type")
    number = versions["version_number"]
    if not isinstance(number["type"], sa.Integer) or number["nullable"]:
        raise RuntimeError(
            "public.post_versions.version_number must be a non-null integer"
        )
    tags = versions["hashtags"]
    if (
        not isinstance(tags["type"], postgresql.ARRAY)
        or not isinstance(tags["type"].item_type, sa.Text)
        or tags["nullable"]
        or not tags.get("default")
    ):
        raise RuntimeError(
            "public.post_versions.hashtags must be non-null TEXT[] with a default"
        )
    for table, col, target in (
        ("posts", "product_id", "products"),
        ("post_versions", "post_id", "posts"),
    ):
        fks = inspector.get_foreign_keys(table, schema="public")
        if not any(
            f["constrained_columns"] == [col]
            and f["referred_schema"] in (None, "public")
            and f["referred_table"] == target
            and f["referred_columns"] == ["id"]
            for f in fks
        ):
            raise RuntimeError(f"public.{table}.{col} has an incompatible foreign key")
    if not any(
        i.get("column_names", [])[:1] == ["product_id"]
        for i in inspector.get_indexes("posts", schema="public")
    ):
        raise RuntimeError("public.posts requires a product_id index")
    uniques = inspector.get_unique_constraints("post_versions", schema="public")
    indexes = inspector.get_indexes("post_versions", schema="public")
    if not any(
        x.get("column_names") == ["post_id", "version_number"] for x in uniques
    ) and not any(
        x.get("unique") and x.get("column_names") == ["post_id", "version_number"]
        for x in indexes
    ):
        raise RuntimeError("post versions require unique (post_id, version_number)")
    checks = {
        c["name"]
        for c in inspector.get_check_constraints("post_versions", schema="public")
    }
    expected_checks = {
        "post_versions_version_number_check",
        "post_versions_headline_check",
        "post_versions_body_check",
        "post_versions_platform_check",
    }
    if not expected_checks.issubset(checks):
        raise RuntimeError(
            "public.post_versions has missing required check constraints"
        )


def create_tables():
    op.create_table(
        "posts",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("public.products.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema="public",
    )
    op.create_index("posts_product_id_idx", "posts", ["product_id"], schema="public")
    op.create_table(
        "post_versions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column(
            "post_id", sa.BigInteger(), sa.ForeignKey("public.posts.id"), nullable=False
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("offer", sa.Text()),
        sa.Column("call_to_action", sa.Text()),
        sa.Column(
            "hashtags",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "post_id", "version_number", name="post_versions_post_id_version_number_key"
        ),
        sa.CheckConstraint(
            "version_number > 0",
            name=sa.schema.conv("post_versions_version_number_check"),
        ),
        sa.CheckConstraint(
            "btrim(headline) <> ''", name=sa.schema.conv("post_versions_headline_check")
        ),
        sa.CheckConstraint(
            "btrim(body) <> ''", name=sa.schema.conv("post_versions_body_check")
        ),
        sa.CheckConstraint(
            "btrim(platform) <> ''", name=sa.schema.conv("post_versions_platform_check")
        ),
        schema="public",
    )


def upgrade():
    if context.is_offline_mode():
        create_tables()
        return
    inspector = sa.inspect(op.get_bind())
    present = [
        inspector.has_table(t, schema="public") for t in ("posts", "post_versions")
    ]
    if all(present):
        validate_existing(inspector)
    elif any(present):
        raise RuntimeError("Partial public posts schema; reconcile before migration")
    else:
        create_tables()


def downgrade():
    raise RuntimeError("Post tables may predate this migration; manual review required")
