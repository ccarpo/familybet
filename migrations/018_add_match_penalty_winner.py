"""
Migration 018: Add penalty_winner to matches

Stores which team won the penalty shootout for KO matches that ended in a draw
after 90 minutes. Values: 'team1', 'team2', or NULL.
"""

VERSION = 18
DESCRIPTION = "Add penalty_winner to matches"


def migrate(conn):
    """Execute migration."""
    cursor = conn.cursor()

    cursor.execute("""
        ALTER TABLE matches
        ADD COLUMN penalty_winner TEXT DEFAULT NULL
    """)

    conn.commit()
