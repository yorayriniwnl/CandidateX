"""Initial database schema for Candidate Capability Intelligence (CCI).

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from cci.db.base import Base
import cci.db.models  # Ensure all model tables are discovered

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
