"""Team utilities for FamilyBet.

This module provides centralized team-related functionality
to ensure consistent team list handling across the application.
"""

from app.models import Match


def get_sorted_unique_teams(include_all=False):
    """Get alphabetically sorted, deduplicated list of all teams.
    
    This function queries all matches and extracts unique team names,
    filtering out placeholder teams and sorting alphabetically.
    
    Args:
        include_all: If True, include placeholder teams like 'TBD', 'TBA'
    
    Returns:
        List of tuples: [(team_name, team_id), ...] sorted by team_name (case-insensitive)
    """
    matches = Match.query.all()
    teams_dict = {}
    
    # Placeholder/unknown team names to filter out
    placeholders = ('TBD', 'TBA', '-', 'Unknown', 'Platzhalter', 'tbd', 'tba')
    
    for match in matches:
        for team_name, team_id in [(match.team1_name, match.team1_id), 
                                   (match.team2_name, match.team2_id)]:
            if not team_name:
                continue
            
            # Filter out placeholder teams unless include_all is True
            if not include_all:
                team_name_lower = team_name.lower()
                if any(p.lower() in team_name_lower for p in placeholders):
                    continue
                # Filter out purely numeric or very short names
                if len(team_name.strip()) < 2:
                    continue
            
            # Keep the first ID we see for each team name
            if team_name not in teams_dict:
                teams_dict[team_name] = team_id
    
    # Return sorted list by team name (case-insensitive)
    return sorted(teams_dict.items(), key=lambda x: x[0].lower())


def get_teams_from_matches(matches):
    """Extract unique, sorted teams from a list of matches.
    
    Args:
        matches: List of Match objects
        
    Returns:
        List of tuples: [(team_name, team_id), ...] sorted by team_name
    """
    teams_dict = {}
    
    for match in matches:
        for team_name, team_id in [(match.team1_name, match.team1_id), 
                                   (match.team2_name, match.team2_id)]:
            if team_name and team_name not in teams_dict:
                teams_dict[team_name] = team_id
    
    return sorted(teams_dict.items(), key=lambda x: x[0].lower())


def get_team_display_name(team_name, team_short=None):
    """Get a formatted display name for a team.
    
    Args:
        team_name: Full team name
        team_short: Short team name (optional)
        
    Returns:
        String: Display name (short if available, otherwise full)
    """
    if team_short:
        return team_short
    return team_name


def is_placeholder_team(team_name):
    """Check if a team name is a placeholder.
    
    Args:
        team_name: Name to check
        
    Returns:
        bool: True if it's a placeholder team
    """
    if not team_name:
        return True
        
    placeholders = ('TBD', 'TBA', '-', 'Unknown', 'Platzhalter', 'tbd', 'tba', 'unknown')
    team_name_lower = team_name.lower()
    
    return any(p.lower() in team_name_lower for p in placeholders) or len(team_name.strip()) < 2
