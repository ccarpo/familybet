"""
Abstract base class for data providers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MatchData:
    """Standardized match data structure."""
    match_id: int
    round_name: str
    round_type: Optional[str]  # 'group', 'knockout', 'special'
    group_order_id: int
    team1_id: int
    team1_name: str
    team1_short: str
    team2_id: int
    team2_name: str
    team2_short: str
    match_date: datetime
    team1_score: Optional[int]
    team2_score: Optional[int]
    is_finished: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easy serialization."""
        return {
            'match_id': self.match_id,
            'round_name': self.round_name,
            'round_type': self.round_type,
            'group_order_id': self.group_order_id,
            'team1_id': self.team1_id,
            'team1_name': self.team1_name,
            'team1_short': self.team1_short,
            'team2_id': self.team2_id,
            'team2_name': self.team2_name,
            'team2_short': self.team2_short,
            'match_date': self.match_date.isoformat() if self.match_date else None,
            'team1_score': self.team1_score,
            'team2_score': self.team2_score,
            'is_finished': self.is_finished,
        }


class DataProvider(ABC):
    """Abstract base class for tournament data providers."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize provider with configuration.
        
        Args:
            config: Provider-specific configuration dict
        """
        self.config = config
    
    @abstractmethod
    def fetch_matches(self, league_shortcut: str, season: int) -> List[MatchData]:
        """
        Fetch match data from the provider.
        
        Args:
            league_shortcut: League identifier (e.g., 'wm2026')
            season: Season year
            
        Returns:
            List of MatchData objects
        """
        pass
    
    @abstractmethod
    def normalize_team_name(self, raw_name: str) -> str:
        """
        Normalize team name from provider format to internal format.
        
        Args:
            raw_name: Raw team name from provider
            
        Returns:
            Normalized team name
        """
        pass
    
    def validate_config(self) -> bool:
        """
        Validate that required configuration is present.
        
        Returns:
            True if config is valid, False otherwise
        """
        return True
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        pass
    
    @property
    @abstractmethod
    def requires_api_key(self) -> bool:
        """Whether this provider requires an API key."""
        pass
