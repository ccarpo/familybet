"""Add location field to matches

Revision ID: 008
Revises: 007
Create Date: 2025-06-17 14:25:00
"""

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def migrate(conn):
    """Add location column to matches table using raw SQL for SQLite compatibility."""
    conn.execute('ALTER TABLE matches ADD COLUMN location VARCHAR(200)')
