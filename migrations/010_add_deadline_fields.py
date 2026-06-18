"""Add deadline_type to tournaments and deadline to tournament_rounds

Revision ID: 010
Revises: 009
Create Date: 2026-06-18
"""

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def migrate(conn):
    """Add deadline fields."""
    conn.execute("ALTER TABLE tournaments ADD COLUMN deadline_type VARCHAR(20) DEFAULT 'match_start'")
    conn.execute("ALTER TABLE tournament_rounds ADD COLUMN deadline DATETIME")
