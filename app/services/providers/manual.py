"""
Manual provider for tournaments without external data source.
This is a no-op provider that returns empty data.
"""

from typing import List, Dict, Any
from .base import DataProvider, MatchData


class ManualProvider(DataProvider):
    """
    Provider for manual tournaments.
    
    This provider does not fetch any data automatically.
    Matches must be created manually by the admin or imported via CSV.
    """
    
    @property
    def provider_name(self) -> str:
        return "Manuell (keine automatische Synchronisation)"
    
    @property
    def requires_api_key(self) -> bool:
        return False
    
    def validate_config(self) -> bool:
        """Manual provider requires no special config."""
        return True
    
    def fetch_matches(self, league_shortcut: str, season: int) -> List[MatchData]:
        """
        Returns empty list - no automatic fetch for manual tournaments.
        
        Args:
            league_shortcut: Ignored for manual provider
            season: Ignored for manual provider
            
        Returns:
            Empty list
        """
        print("[ManualProvider] No automatic sync available. Matches must be created manually or imported via CSV.")
        return []
    
    def normalize_team_name(self, raw_name: str) -> str:
        """Return name as-is for manual provider."""
        return raw_name
