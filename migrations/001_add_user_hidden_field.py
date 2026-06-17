"""
Migration 001: Add is_hidden_from_leaderboard column to users table

Allows administrators to hide users from the leaderboard and betting competition.
"""

VERSION = 1
DESCRIPTION = "Add is_hidden_from_leaderboard column to users table"


def migrate(conn):
    """Execute migration."""
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(users)")
    columns = {column[1] for column in cursor.fetchall()}

    if 'is_hidden_from_leaderboard' not in columns:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN is_hidden_from_leaderboard BOOLEAN DEFAULT 0
        """)

    conn.commit()
