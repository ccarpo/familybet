from flask import Blueprint, request, redirect, url_for, flash, session
from app.models import User, Match, Bet, TournamentBet
from app import db
from datetime import datetime

bets_bp = Blueprint('bets', __name__)

def get_current_user():
    if 'user_id' not in session:
        return None
    return User.query.get(session['user_id'])

def is_admin():
    return session.get('is_admin', False)

@bets_bp.route('/bets', methods=['POST'])
def place_bet():
    user = get_current_user()
    if not user:
        flash('Bitte einloggen', 'error')
        return redirect(url_for('auth.login'))
    
    match_id = request.form.get('match_id', type=int)
    team1_score = request.form.get('team1_score', type=int)
    team2_score = request.form.get('team2_score', type=int)
    on_behalf_of = request.form.get('on_behalf_of', type=int)  # For admin use
    
    if match_id is None or team1_score is None or team2_score is None:
        flash('Bitte alle Felder ausfüllen', 'error')
        return redirect(url_for('main.matches'))
    
    # Validate scores are non-negative
    if team1_score < 0 or team2_score < 0:
        flash('Tore können nicht negativ sein', 'error')
        return redirect(url_for('main.match_detail', match_id=match_id))
    
    match = Match.query.get_or_404(match_id)
    
    # Check if match has already started (unless admin)
    if not is_admin() and match.has_started():
        flash('Spiel hat bereits begonnen - Tipp nicht mehr möglich', 'error')
        return redirect(url_for('main.match_detail', match_id=match_id))
    
    # Determine target user (admin can bet on behalf of others)
    target_user_id = user.id
    if is_admin() and on_behalf_of:
        target_user = User.query.get(on_behalf_of)
        if target_user:
            target_user_id = target_user.id
    
    # Check if bet already exists
    existing_bet = Bet.query.filter_by(user_id=target_user_id, match_id=match_id).first()
    
    if existing_bet:
        # Update existing bet
        existing_bet.team1_score_pred = team1_score
        existing_bet.team2_score_pred = team2_score
        existing_bet.updated_at = datetime.utcnow()
        flash('Tipp aktualisiert!', 'success')
    else:
        # Create new bet
        new_bet = Bet(
            user_id=target_user_id,
            match_id=match_id,
            team1_score_pred=team1_score,
            team2_score_pred=team2_score
        )
        db.session.add(new_bet)
        flash('Tipp abgegeben!', 'success')
    
    db.session.commit()
    
    # If admin was betting for someone else, redirect to admin page
    if is_admin() and on_behalf_of and on_behalf_of != user.id:
        return redirect(url_for('admin.user_bets', user_id=on_behalf_of))
    
    return redirect(url_for('main.match_detail', match_id=match_id))

@bets_bp.route('/tournament-bets', methods=['POST'])
def place_tournament_bet():
    user = get_current_user()
    if not user:
        flash('Bitte einloggen', 'error')
        return redirect(url_for('auth.login'))
    
    winner_team_id = request.form.get('winner_team_id', type=int)
    winner_team_name = request.form.get('winner_team_name', '').strip()
    
    # Get 3 semifinalists (must be different from winner)
    semifinalist1_id = request.form.get('semifinalist1_id', type=int)
    semifinalist1_name = request.form.get('semifinalist1_name', '').strip()
    semifinalist2_id = request.form.get('semifinalist2_id', type=int)
    semifinalist2_name = request.form.get('semifinalist2_name', '').strip()
    semifinalist3_id = request.form.get('semifinalist3_id', type=int)
    semifinalist3_name = request.form.get('semifinalist3_name', '').strip()
    
    # Get target user (admin can bet on behalf of others)
    on_behalf_of = request.form.get('on_behalf_of', type=int)
    target_user_id = user.id
    if is_admin() and on_behalf_of:
        target_user = User.query.get(on_behalf_of)
        if target_user:
            target_user_id = target_user.id
    
    # Validate all teams are selected
    if not winner_team_id or not semifinalist1_id or not semifinalist2_id or not semifinalist3_id:
        flash('Bitte alle 4 Teams auswählen', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Validate winner is not in semifinalists
    semifinalist_ids = {semifinalist1_id, semifinalist2_id, semifinalist3_id}
    if winner_team_id in semifinalist_ids:
        flash('Der Gewinner darf nicht auch als einer der anderen Halbfinalisten gewählt werden', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Validate all semifinalists are different
    if len(semifinalist_ids) != 3:
        flash('Bitte 3 unterschiedliche Halbfinalisten wählen', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Check if tournament has already started (unless admin)
    first_match = Match.query.order_by(Match.match_date).first()
    if first_match and first_match.has_started() and not is_admin():
        flash('Turnier hat bereits begonnen - Tipp nicht mehr möglich', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Check if bet already exists for target user
    existing_bet = TournamentBet.query.filter_by(user_id=target_user_id).first()
    
    if existing_bet:
        # Update existing bet
        existing_bet.winner_team_id = winner_team_id
        existing_bet.winner_team_name = winner_team_name
        existing_bet.semifinalist1_id = semifinalist1_id
        existing_bet.semifinalist1_name = semifinalist1_name
        existing_bet.semifinalist2_id = semifinalist2_id
        existing_bet.semifinalist2_name = semifinalist2_name
        existing_bet.semifinalist3_id = semifinalist3_id
        existing_bet.semifinalist3_name = semifinalist3_name
        existing_bet.updated_at = datetime.utcnow()
        flash('Turniertipp aktualisiert!', 'success')
    else:
        # Create new bet
        new_bet = TournamentBet(
            user_id=target_user_id,
            winner_team_id=winner_team_id,
            winner_team_name=winner_team_name,
            semifinalist1_id=semifinalist1_id,
            semifinalist1_name=semifinalist1_name,
            semifinalist2_id=semifinalist2_id,
            semifinalist2_name=semifinalist2_name,
            semifinalist3_id=semifinalist3_id,
            semifinalist3_name=semifinalist3_name
        )
        db.session.add(new_bet)
        flash('Turniertipp abgegeben!', 'success')
    
    db.session.commit()
    
    # If admin was betting for someone else, redirect back to admin page
    if is_admin() and on_behalf_of and on_behalf_of != user.id:
        return redirect(url_for('admin.user_bets', user_id=on_behalf_of))
    
    return redirect(url_for('main.dashboard'))
