from flask import Blueprint, render_template, session, redirect, url_for, flash
from datetime import datetime
from app.models import User, Match, Bet, TournamentBet
from app.services.scoring import ScoringService

main_bp = Blueprint('main', __name__)

def get_current_user():
    if 'user_id' not in session:
        return None
    return User.query.get(session['user_id'])

@main_bp.before_request
def require_login():
    # Allow access to index without login
    if request.endpoint in ['main.index']:
        return None
    
    if 'user_id' not in session:
        flash('Bitte einloggen', 'error')
        return redirect(url_for('auth.login'))

@main_bp.route('/')
def index():
    user = get_current_user()
    if user:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@main_bp.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))
    
    # Get upcoming matches (next 5 that haven't started)
    now = datetime.utcnow()
    upcoming = Match.query.filter(Match.match_date > now).order_by(Match.match_date).limit(5).all()
    
    # Get user's recent bets
    my_bets = Bet.query.filter_by(user_id=user.id).order_by(Bet.created_at.desc()).limit(5).all()
    
    # Get tournament bet
    tournament_bet = TournamentBet.query.filter_by(user_id=user.id).first()
    
    # Get leaderboard position
    leaderboard = ScoringService.get_leaderboard()
    my_rank = next((entry for entry in leaderboard if entry['user'].id == user.id), None)
    
    return render_template('dashboard.html', 
                          user=user,
                          upcoming_matches=upcoming,
                          my_bets=my_bets,
                          tournament_bet=tournament_bet,
                          my_rank=my_rank,
                          now=now)

@main_bp.route('/matches')
def matches():
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))
    
    # Get all matches grouped by round
    all_matches = Match.query.order_by(Match.match_date).all()
    
    # Group by round
    rounds = {}
    for match in all_matches:
        round_name = match.round_name
        if round_name not in rounds:
            rounds[round_name] = []
        rounds[round_name].append(match)
    
    # Get user's bets for quick lookup
    my_bets = {bet.match_id: bet for bet in Bet.query.filter_by(user_id=user.id).all()}
    
    return render_template('matches.html',
                          rounds=rounds,
                          my_bets=my_bets,
                          now=datetime.utcnow(),
                          user=user)

@main_bp.route('/matches/<int:match_id>')
def match_detail(match_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))
    
    match = Match.query.get_or_404(match_id)
    my_bet = Bet.query.filter_by(user_id=user.id, match_id=match_id).first()
    
    # Get all bets for this match if it's finished
    all_bets = []
    if match.is_finished:
        all_bets = Bet.query.filter_by(match_id=match_id).join(User).all()
    
    return render_template('match_detail.html',
                          match=match,
                          my_bet=my_bet,
                          all_bets=all_bets,
                          now=datetime.utcnow(),
                          user=user)

@main_bp.route('/leaderboard')
def leaderboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))
    
    entries = ScoringService.get_leaderboard()
    
    return render_template('leaderboard.html',
                          entries=entries,
                          user=user)

from flask import request
