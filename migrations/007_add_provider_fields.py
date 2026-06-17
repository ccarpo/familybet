"""
Migration 007: Add provider_type and provider_config to tournaments
"""

VERSION = 7
DESCRIPTION = "Add provider_type and provider_config fields to tournaments for data provider abstraction"


def migrate(conn):
    """Execute the migration."""
    cursor = conn.cursor()
    
    print("[Migration 007] Adding provider fields to tournaments...")
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(tournaments)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Add provider_type
    if 'provider_type' not in columns:
        cursor.execute("ALTER TABLE tournaments ADD COLUMN provider_type TEXT DEFAULT 'openligadb'")
        print("[Migration 007]   ✓ Added provider_type")
    
    # Add provider_config
    if 'provider_config' not in columns:
        cursor.execute("ALTER TABLE tournaments ADD COLUMN provider_config TEXT")
        print("[Migration 007]   ✓ Added provider_config")
    
    # Migrate existing tournaments to use provider_config
    cursor.execute("SELECT id, league_shortcut, season FROM tournaments")
    tournaments = cursor.fetchall()
    
    for tournament_id, league_shortcut, season in tournaments:
        # Build provider_config from existing fields
        config = {}
        if league_shortcut:
            config['league_shortcut'] = league_shortcut
        config['season'] = season
        
        # Store as JSON
        import json
        cursor.execute(
            "UPDATE tournaments SET provider_config = ? WHERE id = ?",
            (json.dumps(config), tournament_id)
        )
    
    conn.commit()
    print(f"[Migration 007]   ✓ Migrated {len(tournaments)} existing tournaments")
    print("[Migration 007] Completed successfully!")
