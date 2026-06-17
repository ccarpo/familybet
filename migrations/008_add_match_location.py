"""Add location field to matches

Revision ID: 008
Revises: 007
Create Date: 2025-06-17 14:25:00
"""

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade(conn):
    """Add location column to matches table using raw SQL for SQLite compatibility."""
    conn.execute('ALTER TABLE matches ADD COLUMN location VARCHAR(200)')


def downgrade(conn):
    """Remove location column - SQLite doesn't support DROP COLUMN directly."""
    # SQLite doesn't support dropping columns, requires table recreation
    # For downgrade, you'd need to create new table without location, copy data, drop old, rename
    pass
