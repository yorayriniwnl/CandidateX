"""add_jd_file_upload_fields

Revision ID: 0002_add_jd_file_upload_fields
Revises: 0001_initial
Create Date: 2026-09-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002_add_jd_file_upload_fields'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    existing_cols = [c['name'] for c in insp.get_columns('job_descriptions')]
    if 'file_name' not in existing_cols:
        op.add_column('job_descriptions', sa.Column('file_name', sa.String(length=500), nullable=True))
    if 'recruitment_rules' not in existing_cols:
        op.add_column('job_descriptions', sa.Column('recruitment_rules', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('job_descriptions', 'recruitment_rules')
    op.drop_column('job_descriptions', 'file_name')
