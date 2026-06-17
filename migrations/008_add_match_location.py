"""Add location field to matches

Revision ID: 008
Revises: 007
Create Date: 2025-06-17 14:25:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    # Add location column to matches table
    op.add_column('matches', sa.Column('location', sa.String(200), nullable=True))


def downgrade():
    # Remove location column
    op.drop_column('matches', 'location')
