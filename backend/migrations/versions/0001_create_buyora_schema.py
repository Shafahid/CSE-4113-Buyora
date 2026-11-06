"""Create the private application schema.

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute(sa.schema.CreateSchema("buyora"))


def downgrade() -> None:
    # No CASCADE: refuse to discard any tables not removed by later migrations.
    op.execute(sa.schema.DropSchema("buyora"))
