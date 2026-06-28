"""
Migration 016: Add penalty_winner to bets

Adds a nullable penalty_winner column to the bets table to store which team
the user predicts will win a KO match in a penalty shootout (when predicting
a draw after 90 minutes).
"""

VERSION = 16
DESCRIPTION = "Add penalty_winner to bets"


def migrate(conn):
    """Execute migration."""
    cursor = conn.cursor()

    cursor.execute("""
        ALTER TABLE bets
        ADD COLUMN penalty_winner TEXT DEFAULT NULL
    """)

    conn.commit()
