"""Cache durable AI persona adaptations without changing historical reports."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "persona_adaptations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "seller_id",
            sa.BigInteger(),
            sa.ForeignKey("public.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.BigInteger(),
            sa.ForeignKey("public.products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("inputs", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB()),
        sa.Column("usage", postgresql.JSONB(), nullable=False),
        sa.Column("error_code", sa.String(40)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("lease_token", sa.String(36)),
        sa.UniqueConstraint("seller_id", "request_id"),
        schema="buyora",
    )
    op.create_index(
        "ix_persona_adaptations_cache",
        "persona_adaptations",
        ["seller_id", "fingerprint"],
        schema="buyora",
    )


def downgrade():
    op.drop_index(
        "ix_persona_adaptations_cache",
        table_name="persona_adaptations",
        schema="buyora",
    )
    op.drop_table("persona_adaptations", schema="buyora")
