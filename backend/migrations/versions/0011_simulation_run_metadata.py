"""Persist run stage and the number of requested personas.

Revision ID: 0011
Revises: 0010

Some existing databases already have this revision applied. Keep these columns
aligned with that schema; historical reports and evaluations are preserved.
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
        sa.Column("stage", sa.String(32), nullable=False, server_default="queued"),
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
        SET expected_personas = CASE
                WHEN jsonb_typeof(run.inputs -> 'personas') = 'array'
                THEN jsonb_array_length(run.inputs -> 'personas')
                ELSE (SELECT count(*) FROM buyora.simulation_run_evaluations AS e
                      WHERE e.run_id = run.id)
            END,
            stage = CASE run.status
                WHEN 'completed' THEN 'report_ready'
                WHEN 'partially_failed' THEN 'report_ready_partial'
                WHEN 'failed' THEN 'failed'
                WHEN 'running' THEN 'evaluating_personas'
                ELSE 'queued'
            END
        """
    )
    op.alter_column(
        "simulation_runs", "expected_personas", nullable=False, schema="buyora"
    )


def downgrade():
    op.drop_column("simulation_runs", "expected_personas", schema="buyora")
    op.drop_column("simulation_runs", "stage", schema="buyora")
