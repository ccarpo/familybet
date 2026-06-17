"""
Migration 006: Add tournament extra points to scoring_config
"""

VERSION = 6
DESCRIPTION = "Add extra points columns (champion, finalist, semifinalist) to scoring_config"


def migrate(conn):
    """Execute the migration."""
    cursor = conn.cursor()
    
    print("[Migration 006] Adding tournament extra points to scoring_config...")
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(scoring_config)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Add champion points
    if 'points_champion' not in columns:
        cursor.execute("ALTER TABLE scoring_config ADD COLUMN points_champion INTEGER DEFAULT 10")
        print("[Migration 006]   ✓ Added points_champion")
    
    # Add finalist points
    if 'points_finalist' not in columns:
        cursor.execute("ALTER TABLE scoring_config ADD COLUMN points_finalist INTEGER DEFAULT 5")
        print("[Migration 006]   ✓ Added points_finalist")
    
    # Add semifinalist points
    if 'points_semifinalist' not in columns:
        cursor.execute("ALTER TABLE scoring_config ADD COLUMN points_semifinalist INTEGER DEFAULT 3")
        print("[Migration 006]   ✓ Added points_semifinalist")
    
    conn.commit()
    print("[Migration 006] Completed successfully!")
