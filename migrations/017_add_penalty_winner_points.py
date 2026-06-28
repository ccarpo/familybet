"""
Migration 017: Add points_penalty_winner to scoring_config

Adds a configurable bonus point for correctly predicting the penalty shootout
winner in a KO round match where a draw (Remis) was predicted.
"""

VERSION = 17
DESCRIPTION = "Add points_penalty_winner to scoring_config"


def migrate(conn):
    """Execute migration."""
    cursor = conn.cursor()

    cursor.execute("""
        ALTER TABLE scoring_config
        ADD COLUMN points_penalty_winner INTEGER DEFAULT 1
    """)

    conn.commit()
