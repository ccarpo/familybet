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
    t_cols = {row[1] for row in conn.execute("PRAGMA table_info(tournaments)")}
    if 'deadline_type' not in t_cols:
        conn.execute("ALTER TABLE tournaments ADD COLUMN deadline_type VARCHAR(20) DEFAULT 'match_start'")

    r_cols = {row[1] for row in conn.execute("PRAGMA table_info(tournament_rounds)")}
    if 'deadline' not in r_cols:
        conn.execute("ALTER TABLE tournament_rounds ADD COLUMN deadline DATETIME")
