"""
Migration 005: Add tournament_id to scoring_config
"""

VERSION = 5
DESCRIPTION = "Add tournament_id to scoring_config for per-tournament scoring"


def migrate(conn):
    """Execute the migration."""
    cursor = conn.cursor()
    
    print("[Migration 005] Adding tournament_id to scoring_config...")
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(scoring_config)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'tournament_id' not in columns:
        cursor.execute("""
            ALTER TABLE scoring_config 
            ADD COLUMN tournament_id INTEGER 
            REFERENCES tournaments(id) ON DELETE CASCADE
        """)
        print("[Migration 005] ✓ Added tournament_id column")
    else:
        print("[Migration 005] tournament_id column already exists")
    
    conn.commit()
    print("[Migration 005] Completed successfully!")
