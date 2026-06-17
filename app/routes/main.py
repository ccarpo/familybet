from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from datetime import datetime
from app import db
from app.models import User, Match, Bet, TournamentBet, ScoringConfig, BettingPhaseLock
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

    # Build deduplicated, sorted teams list for tournament bet dropdown
    teams_dict = {}
    for match in all_matches:
        if match.team1_name and match.team1_name not in ('TBD', 'TBA', '-'):
            teams_dict[match.team1_name] = match.team1_id
        if match.team2_name and match.team2_name not in ('TBD', 'TBA', '-'):
            teams_dict[match.team2_name] = match.team2_id
    sorted_teams = sorted(teams_dict.items(), key=lambda x: x[0])

    # Get phase locks for display
    phase_locks = BettingPhaseLock.get_all_locks()

    return render_template('matches.html',
                          rounds=rounds,
                          my_bets=my_bets,
                          now=datetime.utcnow(),
                          user=user,
                          sorted_teams=sorted_teams,
                          phase_locks=phase_locks)

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


@main_bp.route('/groups')
def groups():
    """Show all groups with standings and matches."""
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    # Get all group matches
    group_matches = Match.query.filter(Match.round_name.like('Gruppe%')).order_by(Match.match_date).all()

    # Group by round_name
    groups_data = {}
    for match in group_matches:
        group_name = match.round_name
        if group_name not in groups_data:
            groups_data[group_name] = {'matches': [], 'teams': {}}
        groups_data[group_name]['matches'].append(match)

        # Track teams for standings
        for team_name, team_id, is_team1 in [(match.team1_name, match.team1_id, True), (match.team2_name, match.team2_id, False)]:
            if team_name not in groups_data[group_name]['teams']:
                groups_data[group_name]['teams'][team_name] = {
                    'id': team_id,
                    'played': 0, 'won': 0, 'drawn': 0, 'lost': 0,
                    'goals_for': 0, 'goals_against': 0, 'points': 0
                }

    # Calculate standings from finished matches
    for group_name, data in groups_data.items():
        for match in data['matches']:
            if match.is_finished and match.team1_score is not None and match.team2_score is not None:
                t1, t2 = match.team1_name, match.team2_name
                s1, s2 = match.team1_score, match.team2_score

                data['teams'][t1]['played'] += 1
                data['teams'][t2]['played'] += 1
                data['teams'][t1]['goals_for'] += s1
                data['teams'][t1]['goals_against'] += s2
                data['teams'][t2]['goals_for'] += s2
                data['teams'][t2]['goals_against'] += s1

                if s1 > s2:
                    data['teams'][t1]['won'] += 1
                    data['teams'][t1]['points'] += 3
                    data['teams'][t2]['lost'] += 1
                elif s2 > s1:
                    data['teams'][t2]['won'] += 1
                    data['teams'][t2]['points'] += 3
                    data['teams'][t1]['lost'] += 1
                else:
                    data['teams'][t1]['drawn'] += 1
                    data['teams'][t2]['drawn'] += 1
                    data['teams'][t1]['points'] += 1
                    data['teams'][t2]['points'] += 1

    # Get user bets
    my_bets = {bet.match_id: bet for bet in Bet.query.filter_by(user_id=user.id).all()}

    # Get phase locks
    phase_locks = BettingPhaseLock.get_all_locks()

    return render_template('groups.html',
                          groups_data=groups_data,
                          my_bets=my_bets,
                          user=user,
                          phase_locks=phase_locks)


@main_bp.route('/round/last16')
def round_last16():
    """Show Sechzehntelfinale (Round of 16) matches."""
    return _show_ko_round('Sechzehntelfinale', 'Sechzehntelfinale')


@main_bp.route('/round/quarter')
def round_quarter():
    """Show Achtelfinale (Round of 8/Quarterfinals) matches."""
    return _show_ko_round('Achtelfinale', 'Achtelfinale')


@main_bp.route('/round/semi')
def round_semi():
    """Show Viertelfinale (Semifinals) matches."""
    return _show_ko_round('Viertelfinale', 'Viertelfinale')


@main_bp.route('/round/final')
def round_final():
    """Show Halbfinale (Finals) matches."""
    return _show_ko_round('Halbfinale', 'Halbfinale')


@main_bp.route('/round/champion')
def round_champion():
    """Show Finale and Spiel um Platz 3."""
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    # Get finale and 3rd place matches
    matches = Match.query.filter(
        db.or_(
            Match.round_name.like('%Finale%'),
            Match.round_name.like('%Platz 3%'),
            Match.round_name.like('%finale%')
        )
    ).order_by(Match.match_date).all()

    # Get user bets
    my_bets = {bet.match_id: bet for bet in Bet.query.filter_by(user_id=user.id).all()}

    # Get phase locks
    phase_locks = BettingPhaseLock.get_all_locks()

    return render_template('ko_round.html',
                          round_name='Finale & Spiel um Platz 3',
                          matches=matches,
                          my_bets=my_bets,
                          user=user,
                          show_qualifiers=False,
                          phase_locks=phase_locks)


def _show_ko_round(round_keyword, display_name):
    """Helper to show knockout round matches."""
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    # Get matches for this round
    matches = Match.query.filter(Match.round_name.like(f'%{round_keyword}%')).order_by(Match.match_date).all()

    # Get user bets
    my_bets = {bet.match_id: bet for bet in Bet.query.filter_by(user_id=user.id).all()}

    # Get qualified teams from groups (for display purposes)
    qualified_teams = _get_qualified_teams()

    # Get phase locks
    phase_locks = BettingPhaseLock.get_all_locks()

    return render_template('ko_round.html',
                          round_name=display_name,
                          matches=matches,
                          my_bets=my_bets,
                          qualified_teams=qualified_teams,
                          user=user,
                          show_qualifiers=True,
                          phase_locks=phase_locks)


def _get_qualified_teams():
    """Calculate which teams have qualified from groups."""
    group_matches = Match.query.filter(Match.round_name.like('Gruppe%')).all()

    groups_data = {}
    for match in group_matches:
        group_name = match.round_name
        if group_name not in groups_data:
            groups_data[group_name] = {}

        for team_name in [match.team1_name, match.team2_name]:
            if team_name not in groups_data[group_name]:
                groups_data[group_name][team_name] = {
                    'played': 0, 'won': 0, 'drawn': 0, 'lost': 0,
                    'goals_for': 0, 'goals_against': 0, 'points': 0
                }

        if match.is_finished and match.team1_score is not None:
            t1, t2 = match.team1_name, match.team2_name
            s1, s2 = match.team1_score, match.team2_score

            for t in [t1, t2]:
                groups_data[group_name][t]['played'] += 1

            groups_data[group_name][t1]['goals_for'] += s1
            groups_data[group_name][t1]['goals_against'] += s2
            groups_data[group_name][t2]['goals_for'] += s2
            groups_data[group_name][t2]['goals_against'] += s1

            if s1 > s2:
                groups_data[group_name][t1]['won'] += 1
                groups_data[group_name][t1]['points'] += 3
                groups_data[group_name][t2]['lost'] += 1
            elif s2 > s1:
                groups_data[group_name][t2]['won'] += 1
                groups_data[group_name][t2]['points'] += 3
                groups_data[group_name][t1]['lost'] += 1
            else:
                groups_data[group_name][t1]['drawn'] += 1
                groups_data[group_name][t2]['drawn'] += 1
                groups_data[group_name][t1]['points'] += 1
                groups_data[group_name][t2]['points'] += 1

    # Get top 2 from each group + best 3rds
    qualified = {'1st': [], '2nd': [], '3rd': []}

    for group_name, teams in groups_data.items():
        # Sort by points, then goal difference
        sorted_teams = sorted(teams.items(), key=lambda x: (x[1]['points'], x[1]['goals_for'] - x[1]['goals_against']), reverse=True)

        if len(sorted_teams) >= 1:
            qualified['1st'].append((group_name, sorted_teams[0][0]))
        if len(sorted_teams) >= 2:
            qualified['2nd'].append((group_name, sorted_teams[1][0]))
        if len(sorted_teams) >= 3:
            qualified['3rd'].append((group_name, sorted_teams[2][0], sorted_teams[2][1]['points']))

    return qualified
