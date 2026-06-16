"""
API-Football client with rate limiting (100 requests/day)
Uses caching to minimize API calls
"""

import requests
import json
import os
from datetime import datetime, timedelta
from flask import current_app


class APIFootballClient:
    """API-Football.com client with aggressive caching for 100 req/day limit"""
    
    BASE_URL = 'https://v3.football.api-sports.io'
    CACHE_DIR = 'cache'
    MAX_REQUESTS_PER_DAY = 100
    
    def __init__(self, api_key=None):
        self.api_key = api_key or current_app.config.get('API_FOOTBALL_KEY', '')
        self.headers = {
            'x-apisports-key': self.api_key
        }
        self._request_count = 0
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """Ensure cache directory exists"""
        if not os.path.exists(self.CACHE_DIR):
            os.makedirs(self.CACHE_DIR)
    
    def _get_cache_path(self, cache_key):
        """Get cache file path for a key"""
        return os.path.join(self.CACHE_DIR, f'{cache_key}.json')
    
    def _get_cached(self, cache_key, max_age_hours=24):
        """Get cached data if still fresh"""
        cache_path = self._get_cache_path(cache_key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                    cached_time = datetime.fromisoformat(cached.get('timestamp', '2000-01-01'))
                    age = datetime.now() - cached_time
                    if age < timedelta(hours=max_age_hours):
                        return cached.get('data')
            except Exception:
                pass
        return None
    
    def _set_cached(self, cache_key, data):
        """Cache data with timestamp"""
        cache_path = self._get_cache_path(cache_key)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'data': data
                }, f)
        except Exception as e:
            print(f'Cache write error: {e}')
    
    def _make_request(self, endpoint, params=None, use_cache=True, cache_hours=24):
        """Make API request with caching and rate limiting"""
        cache_key = f"{endpoint.replace('/', '_')}_{hash(str(params))}"
        
        # Check cache first
        if use_cache:
            cached = self._get_cached(cache_key, cache_hours)
            if cached is not None:
                return cached
        
        # Check request limit
        if self._request_count >= self.MAX_REQUESTS_PER_DAY:
            print(f'WARNING: API request limit reached ({self.MAX_REQUESTS_PER_DAY}/day)')
            return None
        
        url = f'{self.BASE_URL}{endpoint}'
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            self._request_count += 1
            print(f'API-Football request #{self._request_count}: {endpoint}')
            
            response.raise_for_status()
            data = response.json()
            
            # Cache successful response
            if use_cache:
                self._set_cached(cache_key, data)
            
            return data
        except requests.RequestException as e:
            print(f'API-Football Error: {e}')
            return None
    
    def get_leagues(self, season=None, country=None):
        """Get available leagues"""
        params = {}
        if season:
            params['season'] = season
        if country:
            params['country'] = country
        return self._make_request('/leagues', params, cache_hours=168)  # Cache 1 week
    
    def get_fixtures(self, league=None, season=None, from_date=None, to_date=None):
        """Get matches/fixtures"""
        params = {}
        if league:
            params['league'] = league
        if season:
            params['season'] = season
        if from_date:
            params['from'] = from_date
        if to_date:
            params['to'] = to_date
        
        return self._make_request('/fixtures', params, cache_hours=2)  # Cache 2 hours
    
    def get_fixture_by_id(self, fixture_id):
        """Get specific fixture details"""
        return self._make_request(f'/fixtures?id={fixture_id}', cache_hours=1)
    
    def get_teams(self, league=None, season=None):
        """Get teams in a league"""
        params = {}
        if league:
            params['league'] = league
        if season:
            params['season'] = season
        return self._make_request('/teams', params, cache_hours=168)  # Cache 1 week
    
    def get_standings(self, league, season):
        """Get league standings with group info"""
        params = {
            'league': league,
            'season': season
        }
        return self._make_request('/standings', params, cache_hours=2)  # Cache 2 hours


def get_world_cup_2026_league_id():
    """
    World Cup 2026 league ID in API-Football is typically 1 (FIFA World Cup)
    or search by name
    """
    return 1  # FIFA World Cup league ID


def correct_groups_from_apifootball():
    """
    Use API-Football to correct group information from OpenLigaDB.
    Only updates round_name/group info, preserves all other data.
    Minimal API calls with caching.
    """
    from app import db
    from app.models import Match
    
    client = APIFootballClient()
    league_id = get_world_cup_2026_league_id()
    
    # Get standings to extract group info - 1 API call, cached for 2 hours
    standings_data = client.get_standings(league_id, 2026)
    
    corrected_count = 0
    
    if standings_data and 'response' in standings_data:
        for league_standings in standings_data['response']:
            league_info = league_standings.get('league', {})
            standings = league_info.get('standings', [])
            
            # Each group has its own standings array
            for group_standings in standings:
                for team_standing in group_standings:
                    group_name = team_standing.get('group', 'Unknown')
                    team_info = team_standing.get('team', {})
                    team_name = team_info.get('name', '')
                    
                    # Find all matches involving this team and update their group
                    if team_name and 'Gruppe' in group_name:
                        # Convert "Group A" to "Gruppe A"
                        german_group = group_name.replace('Group', 'Gruppe')
                        
                        # Find matches with this team and update group
                        matches = Match.query.filter(
                            db.or_(
                                Match.team1_name == team_name,
                                Match.team2_name == team_name
                            )
                        ).all()
                        
                        for match in matches:
                            if match.round_name != german_group:
                                match.round_name = german_group
                                corrected_count += 1
    
    # Also get fixtures to cross-reference - 1 API call, cached for 2 hours
    fixtures_data = client.get_fixtures(league=league_id, season=2026)
    
    if fixtures_data and 'response' in fixtures_data:
        for fixture in fixtures_data['response']:
            try:
                league = fixture.get('league', {})
                round_info = league.get('round', '')
                
                # Extract group from round info (e.g., "Group Stage - 1" -> "Gruppe ?")
                if 'Group' in round_info:
                    teams = fixture.get('teams', {})
                    home_team = teams.get('home', {}).get('name', '')
                    away_team = teams.get('away', {}).get('name', '')
                    
                    # Try to determine group from standing data we already have
                    # This is backup if standings didn't catch it
                    match = Match.query.filter(
                        Match.team1_name == home_team,
                        Match.team2_name == away_team
                    ).first()
                    
                    if match and 'Gruppe' not in match.round_name:
                        # We couldn't determine exact group, but we know it's group stage
                        pass
            except Exception:
                continue
    
    db.session.commit()
    return corrected_count


def sync_matches_from_apifootball():
    """
    Legacy full sync - prefer using OpenLigaDB as primary + correct_groups_from_apifootball()
    """
    return correct_groups_from_apifootball()
