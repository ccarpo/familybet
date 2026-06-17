"""
OpenLigaDB provider for fetching match data.
"""

import requests
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from .base import DataProvider, MatchData


class OpenLigaDBProvider(DataProvider):
    """Provider for OpenLigaDB API (openligadb.de)."""
    
    BASE_URL = "https://api.openligadb.de"
    
    @property
    def provider_name(self) -> str:
        return "OpenLigaDB"
    
    @property
    def requires_api_key(self) -> bool:
        return False
    
    def validate_config(self) -> bool:
        """Check for required league_shortcut."""
        return 'league_shortcut' in self.config
    
    def fetch_matches(self, league_shortcut: str, season: int) -> List[MatchData]:
        """
        Fetch matches from OpenLigaDB API.
        
        Args:
            league_shortcut: League shortcut (e.g., 'wm2026')
            season: Season year
            
        Returns:
            List of MatchData objects
        """
        url = f"{self.BASE_URL}/getmatchdata/{league_shortcut}/{season}"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            matches_data = response.json()
        except requests.RequestException as e:
            print(f"[OpenLigaDB] Error fetching data: {e}")
            return []
        except ValueError as e:
            print(f"[OpenLigaDB] Error parsing JSON: {e}")
            return []
        
        matches = []
        for match_data in matches_data:
            try:
                match = self._parse_match(match_data)
                if match:
                    matches.append(match)
            except Exception as e:
                print(f"[OpenLigaDB] Error parsing match: {e}")
                continue
        
        return matches
    
    def _parse_match(self, match_data: Dict[str, Any]) -> Optional[MatchData]:
        """Parse raw match data into MatchData object."""
        match_id = match_data.get('matchID')
        if not match_id:
            return None
        
        # Parse team data
        team1 = match_data.get('team1', {})
        team2 = match_data.get('team2', {})
        group = match_data.get('group', {})
        
        # Parse datetime
        match_date = self._parse_datetime(match_data)
        if not match_date:
            return None
        
        # Parse scores
        team1_score, team2_score = self._parse_scores(match_data)
        is_finished = match_data.get('matchIsFinished', False)
        
        # Determine round info
        round_name = group.get('groupName', 'Unknown')
        group_order_id = group.get('groupOrderID', 0)
        
        # Round type will be determined by the caller based on TournamentRound
        round_type = None
        
        return MatchData(
            match_id=match_id,
            round_name=round_name,
            round_type=round_type,
            group_order_id=group_order_id,
            team1_id=team1.get('teamId', 0),
            team1_name=team1.get('teamName', 'Unknown'),
            team1_short=team1.get('shortName', ''),
            team2_id=team2.get('teamId', 0),
            team2_name=team2.get('teamName', 'Unknown'),
            team2_short=team2.get('shortName', ''),
            match_date=match_date,
            team1_score=team1_score,
            team2_score=team2_score,
            is_finished=is_finished
        )
    
    def _parse_datetime(self, match_data: Dict[str, Any]) -> Optional[datetime]:
        """Parse match date and time from various formats."""
        date_str = match_data.get('matchDateTime')
        if not date_str:
            # Try date only
            date_str = match_data.get('matchDateTimeUTC')
        
        if date_str:
            try:
                # Handle ISO format with timezone
                if 'Z' in date_str:
                    date_str = date_str.replace('Z', '+00:00')
                return datetime.fromisoformat(date_str)
            except ValueError:
                pass
        
        return None
    
    def _parse_scores(self, match_data: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
        """Parse final scores from match results."""
        results = match_data.get('matchResults', [])
        
        if not results:
            return None, None
        
        # Find final result (usually orderID 2 or highest)
        final_result = None
        for result in results:
            if result.get('resultName') == 'Endergebnis':
                final_result = result
                break
        
        # If no endergebnis, take highest orderID
        if not final_result:
            final_result = max(results, key=lambda r: r.get('resultOrderID', 0))
        
        if final_result:
            return (
                final_result.get('pointsTeam1'),
                final_result.get('pointsTeam2')
            )
        
        return None, None
    
    def normalize_team_name(self, raw_name: str) -> str:
        """
        Normalize team name from OpenLigaDB format.
        
        Currently just returns the raw name, but can be extended
        for name mapping if needed.
        """
        # Add any name mappings here if needed
        name_mappings = {
            # Example: 'Deutschland' -> 'Germany',
        }
        return name_mappings.get(raw_name, raw_name)
