from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from datetime import datetime
from app.models import User, Match, Bet, TournamentBet, ScoringConfig
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

    # Get last 5 finished matches
    last_matches = Match.query.filter_by(is_finished=True).order_by(Match.match_date.desc()).limit(5).all()

    # Get user's recent bets
    my_bets = Bet.query.filter_by(user_id=user.id).order_by(Bet.created_at.desc()).limit(5).all()

    # Get tournament bet
    tournament_bet = TournamentBet.query.filter_by(user_id=user.id).first()

    # Get full leaderboard (for current ranking display)
    leaderboard = ScoringService.get_leaderboard()
    my_rank = next((entry for entry in leaderboard if entry['user'].id == user.id), None)

    # Get all visible users for game overviews
    from app.models import User
    all_users = User.query.filter_by(is_hidden_from_leaderboard=False).order_by(User.name).all()

    # Get all bets for last 5 and next 5 games
    last_match_ids = [m.id for m in last_matches]
    upcoming_match_ids = [m.id for m in upcoming]
    relevant_match_ids = last_match_ids + upcoming_match_ids

    all_bets_for_display = {}
    if relevant_match_ids:
        bets_query = Bet.query.filter(Bet.match_id.in_(relevant_match_ids)).join(User).all()
        for bet in bets_query:
            if bet.match_id not in all_bets_for_display:
                all_bets_for_display[bet.match_id] = {}
            all_bets_for_display[bet.match_id][bet.user_id] = bet

    return render_template('dashboard.html',
                          user=user,
                          upcoming_matches=upcoming,
                          last_matches=last_matches,
                          my_bets=my_bets,
                          tournament_bet=tournament_bet,
                          leaderboard=leaderboard,
                          my_rank=my_rank,
                          all_users=all_users,
                          all_bets=all_bets_for_display,
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
    
    # Get current scoring config
    scoring_config = ScoringConfig.get_current()
    
    return render_template('match_detail.html',
                          match=match,
                          my_bet=my_bet,
                          all_bets=all_bets,
                          now=datetime.utcnow(),
                          user=user,
                          scoring_config=scoring_config)

@main_bp.route('/history')
def history():
    """Show all finished matches with all bets - the complete betting history."""
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    # Get all finished matches (not just last 5)
    finished_matches = Match.query.filter_by(is_finished=True).order_by(Match.match_date.desc()).all()

    # Get all visible users
    all_users = User.query.filter_by(is_hidden_from_leaderboard=False).order_by(User.name).all()

    # Get all bets for these matches
    match_ids = [m.id for m in finished_matches]
    all_bets_for_display = {}
    if match_ids:
        bets_query = Bet.query.filter(Bet.match_id.in_(match_ids)).join(User).all()
        for bet in bets_query:
            if bet.match_id not in all_bets_for_display:
                all_bets_for_display[bet.match_id] = {}
            all_bets_for_display[bet.match_id][bet.user_id] = bet

    return render_template('history.html',
                          user=user,
                          matches=finished_matches,
                          all_users=all_users,
                          all_bets=all_bets_for_display)

@main_bp.route('/leaderboard')
def leaderboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    entries = ScoringService.get_leaderboard()
    scoring_config = ScoringConfig.get_current()

    return render_template('leaderboard.html',
                          entries=entries,
                          user=user,
                          scoring_config=scoring_config)

@main_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        
        if not name:
            flash('Name ist erforderlich', 'error')
            return render_template('profile.html', user=user)
        
        # Check if email is already used by another user
        if email:
            existing = User.query.filter(User.email == email, User.id != user.id).first()
            if existing:
                flash('Email wird bereits verwendet', 'error')
                return render_template('profile.html', user=user)
        
        user.name = name
        user.email = email
        db.session.commit()
        
        # Update session
        session['user_name'] = user.name
        
        flash('Profil aktualisiert', 'success')
        return redirect(url_for('main.profile'))
    
    return render_template('profile.html', user=user)

from flask import request
