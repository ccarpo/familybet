import requests
from datetime import datetime
from flask import current_app
from app import db
from app.models import Match


class OpenLigaDBClient:
    BASE_URL = 'https://api.openligadb.de'
    
    def __init__(self):
        self.league_shortcut = current_app.config.get('WORLD_CUP_LEAGUE_SHORTCUT', 'wm2026')
        self.season = current_app.config.get('WORLD_CUP_SEASON', 2026)
    
    def _get(self, endpoint, params=None):
        url = f'{self.BASE_URL}{endpoint}'
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f'API Error: {e}')
            return None
    
    def get_available_leagues(self, season=None):
        if season:
            return self._get(f'/getavailableleagues/{season}')
        return self._get('/getavailableleagues')
    
    def get_match_data(self, league_shortcut=None, season=None):
        shortcut = league_shortcut or self.league_shortcut
        s = season or self.season
        return self._get(f'/getmatchdata/{shortcut}/{s}')
    
    def get_match_data_by_group(self, group_order_id, league_shortcut=None, season=None):
        shortcut = league_shortcut or self.league_shortcut
        s = season or self.season
        return self._get(f'/getmatchdata/{shortcut}/{s}/{group_order_id}')
    
    def get_available_groups(self, league_shortcut=None, season=None):
        shortcut = league_shortcut or self.league_shortcut
        s = season or self.season
        return self._get(f'/getavailablegroups/{shortcut}/{s}')
    
    def get_available_teams(self, league_shortcut=None, season=None):
        shortcut = league_shortcut or self.league_shortcut
        s = season or self.season
        return self._get(f'/getavailableteams/{shortcut}/{s}')
    
    def parse_match_datetime(self, match_data):
        """Parse match datetime from API response"""
        try:
            date_str = match_data.get('matchDateTime')
            if date_str:
                # Remove timezone info from string for parsing
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            pass
        return None
    
    def parse_match_results(self, match_data):
        """Extract final scores from match results"""
        results = match_data.get('matchResults', [])
        if not results:
            return None, None
        
        # Get the final result (usually the last one or typeID 2 for end result)
        final_result = None
        for result in results:
            if result.get('resultTypeID') == 2:  # End result
                final_result = result
                break
        
        if not final_result and results:
            final_result = results[-1]  # Take last if no explicit end result
        
        if final_result:
            return final_result.get('pointsTeam1'), final_result.get('pointsTeam2')
        
        return None, None
    
    def sync_matches(self, league_shortcut=None, season=None):
        """Sync matches from OpenLigaDB to local database"""
        from app.services.wm2026_groups import get_team_group
        
        shortcut = league_shortcut or self.league_shortcut
        s = season or self.season
        
        print(f'Syncing matches for {shortcut} season {s}...')
        
        matches_data = self.get_match_data(shortcut, s)
        if not matches_data:
            print('No match data received from API')
            return 0
        
        synced_count = 0
        
        for match_data in matches_data:
            match_id = match_data.get('matchID')
            if not match_id:
                continue
            
            # Check if match already exists
            existing_match = Match.query.filter_by(match_id=match_id).first()
            
            # Parse team data
            team1 = match_data.get('team1', {})
            team2 = match_data.get('team2', {})
            group = match_data.get('group', {})
            
            match_date = self.parse_match_datetime(match_data)
            if not match_date:
                continue
            
            # Get scores if match is finished
            team1_score, team2_score = self.parse_match_results(match_data)
            is_finished = match_data.get('matchIsFinished', False)
            
            # Determine group from hardcoded WM2026 groups
            team1_name = team1.get('teamName', '')
            team2_name = team2.get('teamName', '')
            round_name = get_team_group(team1_name) or get_team_group(team2_name) or 'Unknown'
            
            if existing_match:
                # Update existing match
                existing_match.match_date = match_date
                existing_match.team1_score = team1_score
                existing_match.team2_score = team2_score
                existing_match.is_finished = is_finished
                existing_match.round_name = round_name
                existing_match.last_updated = datetime.utcnow()
            else:
                # Create new match
                new_match = Match(
                    match_id=match_id,
                    league_shortcut=shortcut,
                    league_season=s,
                    round_name=round_name,
                    group_order_id=group.get('groupOrderID', 0),
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
                db.session.add(new_match)
                synced_count += 1
        
        db.session.commit()
        print(f'Synced {synced_count} new matches, updated existing')
        
        # Calculate points for finished matches
        self.calculate_points_for_finished_matches()
        
        return synced_count
    
    def calculate_points_for_finished_matches(self):
        """Calculate points for all bets on finished matches"""
        from app.models import Bet
        
        finished_matches = Match.query.filter_by(is_finished=True).all()
        
        for match in finished_matches:
            if match.team1_score is None or match.team2_score is None:
                continue
            
            bets = Bet.query.filter_by(match_id=match.id).all()
            for bet in bets:
                points = bet.calculate_points(match.team1_score, match.team2_score)
                bet.points_earned = points
        
        db.session.commit()
        print('Calculated points for all finished matches')
