"""
Hardcoded World Cup 2026 Groups (official draw from December 1, 2025)
12 groups (A-L) with 4 teams each = 48 teams total
"""

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


def get_team_group(team_name):
    """Get the group for a given team name"""
    # Normalize team name for comparison
    team_name_normalized = team_name.strip()
    
    for group, teams in WM2026_GROUPS.items():
        for team in teams:
            if team.lower() == team_name_normalized.lower():
                return group
    
    return None


def assign_groups_to_matches():
    """Assign hardcoded groups to all matches in the database"""
    from app import db
    from app.models import Match
    
    matches = Match.query.all()
    updated_count = 0
    
    for match in matches:
        # Try to find group for team1
        group = get_team_group(match.team1_name)
        if group:
            match.round_name = group
            updated_count += 1
            continue
        
        # Try team2 if team1 didn't work
        group = get_team_group(match.team2_name)
        if group:
            match.round_name = group
            updated_count += 1
    
    db.session.commit()
    return updated_count


def get_groups_with_teams():
    """Return the groups dictionary for display"""
    return WM2026_GROUPS
