from flask import Blueprint, jsonify
from app.models import User, Match, Bet, TournamentBet
from app.services.scoring import ScoringService

api_bp = Blueprint('api', __name__)

@api_bp.route('/matches')
def get_matches():
    """Get all matches with results"""
    matches = Match.query.order_by(Match.match_date).all()
    
    result = []
    for match in matches:
        result.append({
            'id': match.id,
            'match_id': match.match_id,
            'round': match.round_name,
            'team1': {
                'id': match.team1_id,
                'name': match.team1_name,
                'short': match.team1_short
            },
            'team2': {
                'id': match.team2_id,
                'name': match.team2_name,
                'short': match.team2_short
            },
            'match_date': match.match_date.isoformat() if match.match_date else None,
            'score1': match.team1_score,
            'score2': match.team2_score,
            'is_finished': match.is_finished
        })
    
    return jsonify(result)

@api_bp.route('/matches/<int:match_id>/bets')
def get_match_bets(match_id):
    """Get all bets for a specific match"""
    match = Match.query.get_or_404(match_id)
    bets = Bet.query.filter_by(match_id=match_id).join(User).all()
    
    result = {
        'match': {
            'id': match.id,
            'team1': match.team1_name,
            'team2': match.team2_name,
            'score1': match.team1_score,
            'score2': match.team2_score,
            'is_finished': match.is_finished
        },
        'bets': []
    }
    
    for bet in bets:
        result['bets'].append({
            'user_id': bet.user_id,
            'user_name': bet.user.name,
            'prediction': f'{bet.team1_score_pred}:{bet.team2_score_pred}',
            'points': bet.points_earned
        })
    
    return jsonify(result)

@api_bp.route('/leaderboard')
def get_leaderboard():
    """Get leaderboard data"""
    entries = ScoringService.get_leaderboard()
    
    result = []
    for entry in entries:
        result.append({
            'rank': entry['rank'],
            'user_id': entry['user'].id,
            'user_name': entry['user'].name,
            'total_points': entry['total_points'],
            'exact_predictions': entry['exact_predictions'],
            'correct_diffs': entry['correct_diffs'],
            'correct_winners': entry['correct_winners'],
            'total_bets': entry['total_bets']
        })
    
    return jsonify(result)

@api_bp.route('/users/<int:user_id>/stats')
def get_user_stats(user_id):
    """Get detailed stats for a user"""
    user = User.query.get_or_404(user_id)
    stats = ScoringService.get_user_stats(user_id)
    
    result = {
        'user_id': user.id,
        'user_name': user.name,
        'total_points': stats['total_points'],
        'exact_predictions': stats['exact_predictions'],
        'correct_diffs': stats['correct_diffs'],
        'correct_winners': stats['correct_winners'],
        'total_bets': stats['total_bets']
    }
    
    # Add tournament bet if exists
    if stats['tournament_bet']:
        result['tournament_bet'] = {
            'winner': stats['tournament_bet'].winner_team_name,
            'semifinalists': [
                stats['tournament_bet'].semifinalist1_name,
                stats['tournament_bet'].semifinalist2_name,
                stats['tournament_bet'].semifinalist3_name
            ],
            'points': stats['tournament_bet'].points_earned
        }
    
    return jsonify(result)

@api_bp.route('/teams')
def get_teams():
    """Get all unique teams from matches"""
    matches = Match.query.all()
    
    teams = {}
    for match in matches:
        if match.team1_id not in teams:
            teams[match.team1_id] = {
                'id': match.team1_id,
                'name': match.team1_name,
                'short': match.team1_short
            }
        if match.team2_id not in teams:
            teams[match.team2_id] = {
                'id': match.team2_id,
                'name': match.team2_name,
                'short': match.team2_short
            }
    
    return jsonify(list(teams.values()))
