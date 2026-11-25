"""Persist simulation job stage and expected persona count.

Revision ID: 0011
Revises: 0010
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "simulation_runs",
        sa.Column(
            "stage",
            sa.String(32),
            nullable=False,
            server_default="queued",
        ),
        schema="buyora",
    )
    op.add_column(
        "simulation_runs",
        sa.Column("expected_personas", sa.Integer(), nullable=True),
        schema="buyora",
    )
    op.execute(
        """
        UPDATE buyora.simulation_runs AS run
        SET expected_personas = (
            SELECT count(*)
            FROM buyora.simulation_run_evaluations AS evaluation
            WHERE evaluation.run_id = run.id
        ),
        stage = CASE
            WHEN run.status = 'running' THEN 'evaluating'
            WHEN run.status = 'completed' THEN 'report_ready'
            WHEN run.status = 'partially_failed' THEN 'report_ready_partial'
            WHEN run.status = 'failed' THEN 'failed'
            ELSE 'queued'
        END
        """
    )
    op.alter_column(
        "simulation_runs",
        "expected_personas",
        nullable=False,
        schema="buyora",
    )


def downgrade():
    op.drop_column("simulation_runs", "expected_personas", schema="buyora")
    op.drop_column("simulation_runs", "stage", schema="buyora")
