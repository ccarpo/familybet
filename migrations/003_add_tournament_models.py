"""
Migration 003: Add Tournament Models

Creates tables for Tournament, TournamentGroup, TournamentTeam, TournamentRound
and populates with WM2026 data.
"""

from datetime import datetime

VERSION = 3
DESCRIPTION = "Add tournament models (Tournament, TournamentGroup, TournamentTeam, TournamentRound)"


def migrate(conn):
    """Execute the migration using sqlite3 connection."""
    cursor = conn.cursor()
    
    print("[Migration 003] Creating tournament tables...")
    
    # Create tournaments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            short_name TEXT NOT NULL UNIQUE,
            season INTEGER NOT NULL,
            is_active INTEGER DEFAULT 0,
            league_shortcut TEXT,
            num_groups INTEGER DEFAULT 12,
            teams_per_group INTEGER DEFAULT 4,
            has_knockout_stage INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create tournament_groups table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournament_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            code TEXT NOT NULL,
            order_index INTEGER DEFAULT 0
        )
    """)
    
    # Create tournament_teams table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournament_teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            group_id INTEGER REFERENCES tournament_groups(id) ON DELETE SET NULL,
            team_name TEXT NOT NULL,
            team_id INTEGER,
            qualified_position INTEGER
        )
    """)
    
    # Create tournament_rounds table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournament_rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            round_type TEXT NOT NULL,
            phase_key TEXT,
            order_index INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    print("[Migration 003] ✓ Tournament tables created")
    
    # Populate with WM2026 data
    populate_wm2026(conn)
    
    print("[Migration 003] Completed successfully!")


def populate_wm2026(conn):
    """Populate WM2026 tournament data."""
    cursor = conn.cursor()
    print("[Migration 003] Populating WM2026 data...")
    
    WM2026_GROUPS = {
        'Gruppe A': ['Mexiko', 'Südafrika', 'Südkorea', 'Tschechien'],
        'Gruppe B': ['Kanada', 'Bosnien-Herzegowina', 'USA', 'Paraguay'],
        'Gruppe C': ['Katar', 'Schweiz', 'Brasilien', 'Marokko'],
        'Gruppe D': ['Haiti', 'Schottland', 'Australien', 'Türkei'],
        'Gruppe E': ['Deutschland', 'Curaçao', 'Niederlande', 'Japan'],
        'Gruppe F': ['Elfenbeinküste', 'Ecuador', 'Schweden', 'Tunesien'],
        'Gruppe G': ['Spanien', 'Kap Verde', 'Saudi-Arabien', 'Uruguay'],
        'Gruppe H': ['Belgien', 'Ägypten', 'Iran', 'Neuseeland'],
        'Gruppe I': ['Frankreich', 'Senegal', 'Irak', 'Norwegen'],
        'Gruppe J': ['Argentinien', 'Algerien', 'Österreich', 'Jordanien'],
        'Gruppe K': ['Portugal', 'DR Kongo', 'Ghana', 'Panama'],
        'Gruppe L': ['England', 'Kroatien', 'Usbekistan', 'Kolumbien'],
    }
    
    KNOCKOUT_ROUNDS = [
        ('Sechzehntelfinale', 'sechzehntelfinale', 2),
        ('Achtelfinale', 'achtelfinale', 3),
        ('Viertelfinale', 'viertelfinale', 4),
        ('Halbfinale', 'halbfinale', 5),
        ('Spiel um Platz 3', 'finale', 6),
        ('Finale', 'finale', 7),
    ]
    
    # Check if WM2026 already exists
    cursor.execute("SELECT id FROM tournaments WHERE short_name = 'wm2026'")
    existing = cursor.fetchone()
    
    if existing:
        print("[Migration 003]   WM2026 tournament already exists, skipping creation")
        return
    
    now = datetime.utcnow().isoformat()
    
    # Insert tournament
    cursor.execute("""
        INSERT INTO tournaments (name, short_name, season, is_active, league_shortcut, 
                                 num_groups, teams_per_group, has_knockout_stage, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ('FIFA World Cup 2026', 'wm2026', 2026, 1, 'wm2026', 12, 4, 1, now, now))
    
    # Get tournament ID
    cursor.execute("SELECT id FROM tournaments WHERE short_name = 'wm2026'")
    tournament_id = cursor.fetchone()[0]
    print(f"[Migration 003]   Created tournament with ID: {tournament_id}")
    
    # Insert groups
    group_ids = {}
    for i, (group_name, teams) in enumerate(WM2026_GROUPS.items(), 1):
        code = group_name.replace('Gruppe ', '')
        cursor.execute("""
            INSERT INTO tournament_groups (tournament_id, name, code, order_index)
            VALUES (?, ?, ?, ?)
        """, (tournament_id, group_name, code, i))
        
        # Get group ID
        cursor.execute(
            "SELECT id FROM tournament_groups WHERE tournament_id = ? AND code = ?",
            (tournament_id, code)
        )
        group_ids[group_name] = cursor.fetchone()[0]
    
    print(f"[Migration 003]   Created {len(group_ids)} groups")
    
    # Get team IDs from matches table
    team_name_to_id = {}
    try:
        cursor.execute("SELECT DISTINCT team1_name, team1_id FROM matches WHERE league_shortcut = 'wm2026'")
        for row in cursor.fetchall():
            if row[0] and row[1]:
                team_name_to_id[row[0]] = row[1]
        
        cursor.execute("SELECT DISTINCT team2_name, team2_id FROM matches WHERE league_shortcut = 'wm2026'")
        for row in cursor.fetchall():
            if row[0] and row[1]:
                team_name_to_id[row[0]] = row[1]
    except:
        # matches table might not exist yet or be empty
        pass
    
    # Insert teams
    teams_count = 0
    for group_name, teams in WM2026_GROUPS.items():
        group_id = group_ids[group_name]
        for team_name in teams:
            team_id = team_name_to_id.get(team_name)
            cursor.execute("""
                INSERT INTO tournament_teams (tournament_id, group_id, team_name, team_id, qualified_position)
                VALUES (?, ?, ?, ?, NULL)
            """, (tournament_id, group_id, team_name, team_id))
            teams_count += 1
    
    print(f"[Migration 003]   Created {teams_count} teams")
    
    # Insert knockout rounds
    for round_name, phase_key, order_idx in KNOCKOUT_ROUNDS:
        round_type = 'knockout' if 'finale' in phase_key else 'special'
        cursor.execute("""
            INSERT INTO tournament_rounds (tournament_id, name, round_type, phase_key, order_index)
            VALUES (?, ?, ?, ?, ?)
        """, (tournament_id, round_name, round_type, phase_key, order_idx))
    
    # Also add group rounds
    for group_name in WM2026_GROUPS.keys():
        cursor.execute("""
            INSERT INTO tournament_rounds (tournament_id, name, round_type, phase_key, order_index)
            VALUES (?, ?, 'group', 'gruppenphase', 1)
        """, (tournament_id, group_name))
    
    print(f"[Migration 003]   Created {len(KNOCKOUT_ROUNDS) + len(WM2026_GROUPS)} rounds")
    
    conn.commit()
    print("[Migration 003]   ✓ WM2026 data populated")
