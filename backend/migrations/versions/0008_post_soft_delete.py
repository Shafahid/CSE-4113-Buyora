"""Keep revision 0008 for databases that may already have applied it.

Revision ID: 0008
Revises: 0007

The application no longer uses posts.deleted_at. Leave any existing column
untouched so upgrading or downgrading this revision does not destroy data.
"""

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
