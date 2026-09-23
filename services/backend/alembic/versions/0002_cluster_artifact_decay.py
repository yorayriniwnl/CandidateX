"""Persist within-cluster artifact diminishing returns.

Revision ID: 0002_cluster_artifact_decay
Revises: 0001_initial_schema
Create Date: 2026-09-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_cluster_artifact_decay"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "scoring_configs" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("scoring_configs")}
    if "cluster_artifact_decay" not in existing:
        op.add_column(
            "scoring_configs",
            sa.Column(
                "cluster_artifact_decay",
                sa.Float(),
                nullable=False,
                server_default=sa.text("0.5"),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "scoring_configs" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("scoring_configs")}
    if "cluster_artifact_decay" in existing:
        op.drop_column("scoring_configs", "cluster_artifact_decay")
