"""Add selected_tournament_id to users

Revision ID: 009
Revises: 008
Create Date: 2025-06-17 16:45:00
"""

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def migrate(conn):
    """Add selected_tournament_id column to users table."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    if 'selected_tournament_id' not in cols:
        conn.execute('ALTER TABLE users ADD COLUMN selected_tournament_id INTEGER REFERENCES tournaments(id)')
