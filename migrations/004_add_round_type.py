"""
Migration 004: Add round_type to matches and populate from TournamentRound
"""

VERSION = 4
DESCRIPTION = "Add round_type column to matches and populate from TournamentRound"


def migrate(conn):
    """Execute the migration."""
    cursor = conn.cursor()
    
    print("[Migration 004] Adding round_type column to matches...")
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(matches)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'round_type' not in columns:
        cursor.execute("ALTER TABLE matches ADD COLUMN round_type TEXT")
        print("[Migration 004] ✓ Added round_type column")
    else:
        print("[Migration 004] round_type column already exists")
    
    # Populate round_type from TournamentRound data
    print("[Migration 004] Populating round_type from TournamentRound...")
    
    # Get active tournament
    cursor.execute("SELECT id FROM tournaments WHERE is_active = 1")
    result = cursor.fetchone()
    
    if result:
        tournament_id = result[0]
        
        # Get all rounds for this tournament
        cursor.execute("""
            SELECT name, round_type FROM tournament_rounds 
            WHERE tournament_id = ?
        """, (tournament_id,))
        
        rounds = cursor.fetchall()
        
        # Update matches based on round_name matching
        updated_count = 0
        for round_name, round_type in rounds:
            cursor.execute("""
                UPDATE matches 
                SET round_type = ? 
                WHERE round_name = ?
            """, (round_type, round_name))
            updated_count += cursor.rowcount
        
        conn.commit()
        print(f"[Migration 004] ✓ Updated {updated_count} matches with round_type")
    else:
        print("[Migration 004] No active tournament found, skipping round_type population")
    
    print("[Migration 004] Completed successfully!")
