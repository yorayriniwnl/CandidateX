"""Persist evidence family identity and scoring decay.

Revision ID: 0003_evidence_family_correlation
Revises: 0002_cluster_artifact_decay
Create Date: 2026-09-23 00:00:00.000000
"""

import hashlib

from alembic import op
import sqlalchemy as sa


revision = "0003_evidence_family_correlation"
down_revision = "0002_cluster_artifact_decay"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if "evidence" in tables:
        columns = {
            column["name"]: column
            for column in sa.inspect(bind).get_columns("evidence")
        }
        if "evidence_family_id" not in columns:
            op.add_column(
                "evidence",
                sa.Column("evidence_family_id", sa.String(length=68), nullable=True),
            )
        if "observation_type" not in columns:
            op.add_column(
                "evidence",
                sa.Column("observation_type", sa.String(length=100), nullable=True),
            )

        rows = bind.execute(
            sa.text(
                "SELECT id, evidence_family_id, observation_type FROM evidence"
            )
        ).all()
        for row in rows:
            evidence_id = str(row.id)
            family_id = row.evidence_family_id or (
                "ef0:" + hashlib.sha256(evidence_id.encode()).hexdigest()
            )
            observation_type = row.observation_type or "legacy_unknown"
            if row.evidence_family_id is None or row.observation_type is None:
                bind.execute(
                    sa.text(
                        "UPDATE evidence SET evidence_family_id = :family_id, "
                        "observation_type = :observation_type WHERE id = :evidence_id"
                    ),
                    {
                        "family_id": family_id,
                        "observation_type": observation_type,
                        "evidence_id": row.id,
                    },
                )

        refreshed = {
            column["name"]: column
            for column in sa.inspect(bind).get_columns("evidence")
        }
        needs_nonnull = [
            name
            for name in ("evidence_family_id", "observation_type")
            if refreshed[name]["nullable"]
        ]
        cluster_column = refreshed.get("cluster_id")
        widen_cluster_id = (
            cluster_column is not None
            and getattr(cluster_column["type"], "length", None) is not None
            and cluster_column["type"].length < 255
        )
        if needs_nonnull or widen_cluster_id:
            with op.batch_alter_table("evidence") as batch:
                if "evidence_family_id" in needs_nonnull:
                    batch.alter_column(
                        "evidence_family_id",
                        existing_type=sa.String(length=68),
                        nullable=False,
                    )
                if "observation_type" in needs_nonnull:
                    batch.alter_column(
                        "observation_type",
                        existing_type=sa.String(length=100),
                        nullable=False,
                    )
                if widen_cluster_id:
                    batch.alter_column(
                        "cluster_id",
                        existing_type=cluster_column["type"],
                        type_=sa.String(length=255),
                        existing_nullable=cluster_column["nullable"],
                    )

    if "scoring_configs" in tables:
        scoring_columns = {
            column["name"]
            for column in sa.inspect(bind).get_columns("scoring_configs")
        }
        if "evidence_family_decay" not in scoring_columns:
            op.add_column(
                "scoring_configs",
                sa.Column(
                    "evidence_family_decay",
                    sa.Float(),
                    nullable=False,
                    server_default=sa.text("0.5"),
                ),
            )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "scoring_configs" in tables:
        columns = {
            column["name"]
            for column in sa.inspect(bind).get_columns("scoring_configs")
        }
        if "evidence_family_decay" in columns:
            op.drop_column("scoring_configs", "evidence_family_decay")

    if "evidence" in tables:
        columns = {
            column["name"] for column in sa.inspect(bind).get_columns("evidence")
        }
        if "observation_type" in columns:
            op.drop_column("evidence", "observation_type")
        if "evidence_family_id" in columns:
            op.drop_column("evidence", "evidence_family_id")
