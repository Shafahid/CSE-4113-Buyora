"""Add competitor provenance and private optional-AI admission reservations.

Revision ID: 0017
Revises: 0016
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "competitor_evidence", sa.Column("source_url", sa.Text()), schema="public"
    )
    op.add_column(
        "competitor_evidence", sa.Column("source_note", sa.Text()), schema="public"
    )
    op.create_table(
        "ai_request_reservations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "seller_id",
            sa.BigInteger(),
            sa.ForeignKey("public.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("resource_id", sa.BigInteger(), nullable=False),
        sa.Column("reserved_tokens", sa.Integer(), nullable=False),
        sa.Column("policy", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("kind", "resource_id", name="uq_ai_reservation_resource"),
        sa.CheckConstraint(
            "reserved_tokens > 0",
            name=op.f("ck_ai_request_reservations_ai_reserved_tokens_positive"),
        ),
        schema="buyora",
    )
    op.create_index(
        "ix_ai_reservations_seller_created",
        "ai_request_reservations",
        ["seller_id", "created_at"],
        schema="buyora",
    )
    op.execute("REVOKE ALL ON TABLE buyora.ai_request_reservations FROM PUBLIC")
    for role in ("anon", "authenticated"):
        op.execute(
            f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles "
            f"WHERE rolname = '{role}') THEN REVOKE ALL ON TABLE "
            f"buyora.ai_request_reservations FROM {role}; END IF; END $$"
        )


def downgrade():
    raise RuntimeError(
        "Provenance and AI reservations may contain data; manual review required"
    )
