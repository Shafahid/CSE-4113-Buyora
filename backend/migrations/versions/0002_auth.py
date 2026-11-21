"""Create private seller authentication tables.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import context, op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def create_tables():
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(512), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema="public",
    )
    op.create_index(
        "uq_users_email_lower",
        "users",
        [sa.text("lower(email)")],
        unique=True,
        schema="public",
    )
    op.create_table(
        "user_profiles",
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("public.users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema="public",
    )
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("public.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        schema="public",
    )
    op.create_index(
        "ix_auth_sessions_user_id", "auth_sessions", ["user_id"], schema="public"
    )


def is_lower_email_index(index):
    expressions = [
        expression.lower().replace(" ", "")
        for expression in index.get("expressions", [])
        if expression
    ]
    return bool(index.get("unique")) and expressions in (
        ["lower(email)"],
        ["lower(email::text)"],
    )


def validate_existing(inspector):
    expected = {
        "users": {
            "id": ("BIGINT", False),
            "email": ("text", False),
            "password_hash": ("text", False),
            "created_at": ("timestamp", False),
        },
        "user_profiles": {
            "user_id": ("BIGINT", False),
            "display_name": ("text", False),
            "created_at": ("timestamp", False),
        },
        "auth_sessions": {
            "id": ("BIGINT", False),
            "user_id": ("BIGINT", False),
            "token_hash": ("text", False),
            "created_at": ("timestamp", False),
            "expires_at": ("timestamp", False),
            "revoked_at": ("timestamp", True),
        },
    }
    for table, columns in expected.items():
        actual = {
            col["name"]: col for col in inspector.get_columns(table, schema="public")
        }
        if not set(columns).issubset(actual):
            raise RuntimeError(
                f"public.{table} has missing columns; reconcile before migration"
            )
        for name, (kind, nullable) in columns.items():
            col = actual[name]
            typ = col["type"]
            valid = (
                isinstance(typ, sa.BigInteger)
                if kind == "BIGINT"
                else isinstance(typ, (sa.String, sa.Text))
                if kind == "text"
                else isinstance(typ, sa.DateTime) and typ.timezone
            )
            if not valid or col["nullable"] != nullable:
                raise RuntimeError(
                    f"public.{table}.{name} is incompatible; reconcile before migration"
                )
        pk = inspector.get_pk_constraint(table, schema="public")["constrained_columns"]
        if pk != (["user_id"] if table == "user_profiles" else ["id"]):
            raise RuntimeError(f"public.{table} has an incompatible primary key")
    for table in ("users", "auth_sessions"):
        col = next(
            x
            for x in inspector.get_columns(table, schema="public")
            if x["name"] == "id"
        )
        if not col.get("identity") and not col.get("default"):
            raise RuntimeError(f"public.{table}.id must generate IDs")
    for table in ("user_profiles", "auth_sessions"):
        fks = inspector.get_foreign_keys(table, schema="public")
        if not any(
            f["constrained_columns"] == ["user_id"]
            and f["referred_schema"] in (None, "public")
            and f["referred_table"] == "users"
            and f["referred_columns"] == ["id"]
            for f in fks
        ):
            raise RuntimeError(f"public.{table} must reference public.users")
    indexes = inspector.get_indexes("users", schema="public")
    if not any(is_lower_email_index(i) for i in indexes):
        raise RuntimeError("public.users needs a unique index on lower(email)")
    indexes = inspector.get_indexes("auth_sessions", schema="public")
    uniques = inspector.get_unique_constraints("auth_sessions", schema="public")
    if not any(
        x.get("column_names") == ["token_hash"] and x.get("unique") for x in indexes
    ) and not any(x.get("column_names") == ["token_hash"] for x in uniques):
        raise RuntimeError("public.auth_sessions.token_hash must be unique")
    if not any(x.get("column_names", [])[:1] == ["user_id"] for x in indexes):
        raise RuntimeError("public.auth_sessions.user_id needs an index")


def upgrade():
    if context.is_offline_mode():
        create_tables()
    else:
        inspector = sa.inspect(op.get_bind())
        tables = ("users", "user_profiles", "auth_sessions")
        present = [inspector.has_table(table, schema="public") for table in tables]
        if any(present) and not all(present):
            raise RuntimeError(
                "Partial public auth schema: reconcile tables before migration"
            )
        if all(present):
            validate_existing(inspector)
        else:
            create_tables()
    for table in ("users", "user_profiles", "auth_sessions"):
        op.execute(sa.text(f"REVOKE ALL ON TABLE public.{table} FROM PUBLIC"))
        op.execute(sa.text(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY"))
        for role in ("anon", "authenticated"):
            op.execute(
                sa.text(
                    f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles "
                    f"WHERE rolname = '{role}') "
                    f"THEN REVOKE ALL ON TABLE public.{table} FROM {role}; "
                    "END IF; END $$"
                )
            )


def downgrade():
    raise RuntimeError(
        "Auth tables may contain pre-existing data; downgrade requires manual review"
    )
