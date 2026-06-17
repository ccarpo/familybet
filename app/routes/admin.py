from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import User, Match, Bet, ScoringConfig, BettingPhaseLock
from app import db
from app.services.scheduler import trigger_manual_sync
from app.services.scoring import ScoringService

admin_bp = Blueprint('admin', __name__)

def require_admin():
    if not session.get('is_admin'):
        flash('Admin-Zugriff erforderlich', 'error')
        return redirect(url_for('auth.login'))

def get_current_user():
    if 'user_id' not in session:
        return None
    return User.query.get(session['user_id'])

@admin_bp.before_request
def check_admin():
    if not session.get('is_admin'):
        flash('Admin-Zugriff erforderlich', 'error')
        return redirect(url_for('auth.login'))

@admin_bp.route('/admin')
def index():
    user = get_current_user()
    
    # Get stats
    total_users = User.query.count()
    total_matches = Match.query.count()
    finished_matches = Match.query.filter_by(is_finished=True).count()
    total_bets = Bet.query.count()
    
    # Get all users
    users = User.query.all()
    
    # Get current scoring config
    scoring_config = ScoringConfig.get_current()
    
    return render_template('admin/index.html',
                          user=user,
                          stats={
                              'total_users': total_users,
                              'total_matches': total_matches,
                              'finished_matches': finished_matches,
                              'total_bets': total_bets
                          },
                          users=users,
                          scoring_config=scoring_config)

@admin_bp.route('/admin/scoring', methods=['POST'])
def update_scoring():
    try:
        points_exact = int(request.form.get('points_exact', 3))
        points_diff = int(request.form.get('points_diff', 2))
        points_winner = int(request.form.get('points_winner', 1))
        
        # Validate inputs
        if points_exact < 0 or points_diff < 0 or points_winner < 0:
            flash('Punkte können nicht negativ sein', 'error')
            return redirect(url_for('admin.index'))
        
        # Create new config
        ScoringConfig.create_new(points_exact, points_diff, points_winner)
        
        # Recalculate all points with new config
        ScoringService.recalculate_all_match_points()
        
        flash(f'Punktesystem aktualisiert: Exakt={points_exact}, Diff={points_diff}, Sieger={points_winner}. Alle Punkte wurden neu berechnet.', 'success')
    except ValueError:
        flash('Bitte gültige Zahlen eingeben', 'error')
    except Exception as e:
        flash(f'Aktualisierung fehlgeschlagen: {str(e)}', 'error')
    
    return redirect(url_for('admin.index'))

@admin_bp.route('/admin/users', methods=['POST'])
def add_user():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip().lower()
    is_admin_user = request.form.get('is_admin') == 'on'
    
    if not name:
        flash('Name ist erforderlich', 'error')
        return redirect(url_for('admin.index'))
    
    # Check if email already exists
    if email:
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('Email wird bereits verwendet', 'error')
            return redirect(url_for('admin.index'))
    
    new_user = User(name=name, email=email, is_admin=is_admin_user)
    db.session.add(new_user)
    db.session.commit()
    
    flash(f'Benutzer {name} erstellt', 'success')
    return redirect(url_for('admin.index'))

@admin_bp.route('/admin/assign-groups', methods=['POST'])
def assign_groups():
    """Assign hardcoded WM2026 groups to all matches"""
    try:
        from app.services.wm2026_groups import assign_groups_to_matches
        count = assign_groups_to_matches()
        flash(f'{count} Spiele wurden den korrekten WM2026 Gruppen zugeordnet', 'success')
    except Exception as e:
        flash(f'Fehler bei Gruppenzuordnung: {str(e)}', 'error')
    
    return redirect(url_for('admin.check_data'))

@admin_bp.route('/admin/check-data')
def check_data():
    """Check OpenLigaDB data and groups"""
    # Get all matches grouped by round
    from app.models import Match
    matches = Match.query.order_by(Match.match_date).all()
    
    rounds = {}
    for match in matches:
        if match.round_name not in rounds:
            rounds[match.round_name] = []
        rounds[match.round_name].append(match)
    
    return render_template('admin/check_data.html', rounds=rounds)

@admin_bp.route('/admin/sync-apifootball', methods=['POST'])
def sync_apifootball():
    """Sync matches from API-Football (100 req/day limit)"""
    try:
        from app.services.apifootball import sync_matches_from_apifootball
        count = sync_matches_from_apifootball()
        flash(f'{count} Spiele von API-Football synchronisiert (mit Caching)', 'success')
    except Exception as e:
        flash(f'Fehler bei API-Football Sync: {str(e)}', 'error')
    
    return redirect(url_for('admin.index'))

@admin_bp.route('/admin/edit-groups', methods=['GET', 'POST'])
def edit_groups():
    """Manually edit group assignments - team based"""
    from app.models import Match
    from collections import defaultdict
    
    if request.method == 'POST':
        action = request.form.get('action', '')
        
        if action == 'move_team':
            # Move all matches for a team to a new group
            team_name = request.form.get('team_name', '').strip()
            new_group = request.form.get('new_group', '').strip()
            
            if team_name and new_group:
                matches = Match.query.filter(
                    db.or_(
                        Match.team1_name == team_name,
                        Match.team2_name == team_name
                    )
                ).all()
                
                updated_count = 0
                for match in matches:
                    # Update all group stage matches for this team (only if not already in target group)
                    if ('Gruppe' in match.round_name or match.round_name == 'Unknown') and match.round_name != new_group:
                        match.round_name = new_group
                        updated_count += 1
                
                db.session.commit()
                flash(f'Team {team_name} wurde nach {new_group} verschoben ({updated_count} Spiele aktualisiert)', 'success')
        
        return redirect(url_for('admin.edit_groups'))
    
    # Get all matches
    all_matches = Match.query.all()
    
    # Extract all teams and their current groups
    teams_data = defaultdict(lambda: {'group': 'Unknown', 'matches': []})
    
    for match in all_matches:
        t1_name = match.team1_name
        t2_name = match.team2_name
        
        # Track group info for each team
        if 'Gruppe' in match.round_name:
            teams_data[t1_name]['group'] = match.round_name
            teams_data[t2_name]['group'] = match.round_name
        
        teams_data[t1_name]['matches'].append(match)
        teams_data[t2_name]['matches'].append(match)
    
    # Group teams by their assigned group
    groups = defaultdict(list)
    unassigned = []
    
    for team_name, data in teams_data.items():
        if 'Gruppe' in data['group']:
            groups[data['group']].append(team_name)
        else:
            unassigned.append(team_name)
    
    # Get group matches for display
    group_matches = {}
    for group_name in ['Gruppe A', 'Gruppe B', 'Gruppe C', 'Gruppe D', 
                       'Gruppe E', 'Gruppe F', 'Gruppe G', 'Gruppe H',
                       'Gruppe I', 'Gruppe J', 'Gruppe K', 'Gruppe L']:
        group_matches[group_name] = Match.query.filter_by(round_name=group_name).order_by(Match.match_date).all()
    
    return render_template('admin/edit_groups.html', 
                          groups=dict(groups), 
                          unassigned=unassigned,
                          group_matches=group_matches,
                          teams_data=dict(teams_data))

@admin_bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
def edit_user(user_id):
    target_user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        is_admin_user = request.form.get('is_admin') == 'on'
        
        if not name:
            flash('Name ist erforderlich', 'error')
            return render_template('admin/edit_user.html', target_user=target_user)
        
        # Check if email is already used by another user
        if email:
            existing = User.query.filter(User.email == email, User.id != user_id).first()
            if existing:
                flash('Email wird bereits verwendet', 'error')
                return render_template('admin/edit_user.html', target_user=target_user)
        
        target_user.name = name
        target_user.email = email
        target_user.is_admin = is_admin_user
        db.session.commit()
        
        flash(f'Benutzer {name} aktualisiert', 'success')
        return redirect(url_for('admin.index'))
    
    return render_template('admin/edit_user.html', target_user=target_user)

@admin_bp.route('/admin/users/<int:user_id>')
def user_bets(user_id):
    user = get_current_user()
    target_user = User.query.get_or_404(user_id)

    # Get all matches
    all_matches = Match.query.order_by(Match.match_date).all()

    # Get user's bets
    user_bets = {bet.match_id: bet for bet in Bet.query.filter_by(user_id=user_id).all()}

    # Get sorted teams for tournament bet dropdown
    from app.services.teams import get_sorted_unique_teams
    sorted_teams = get_sorted_unique_teams()

    return render_template('admin/user_bets.html',
                          user=user,
                          target_user=target_user,
                          matches=all_matches,
                          user_bets=user_bets,
                          sorted_teams=sorted_teams)

@admin_bp.route('/admin/users/<int:user_id>/toggle-visibility', methods=['POST'])
def toggle_user_visibility(user_id):
    """Toggle whether a user is hidden from the leaderboard/competition"""
    target_user = User.query.get_or_404(user_id)

    # Toggle the visibility status
    target_user.is_hidden_from_leaderboard = not target_user.is_hidden_from_leaderboard
    db.session.commit()

    status = "ausgeblendet" if target_user.is_hidden_from_leaderboard else "wieder sichtbar"
    flash(f'Benutzer {target_user.name} ist jetzt {status} in der Rangliste', 'success')

    return redirect(url_for('admin.index'))

@admin_bp.route('/admin/sync', methods=['POST'])
def sync_matches():
    try:
        synced = trigger_manual_sync()
        flash(f'{synced} neue Spiele synchronisiert', 'success')
    except Exception as e:
        flash(f'Synchronisation fehlgeschlagen: {str(e)}', 'error')
    
    return redirect(url_for('admin.index'))

@admin_bp.route('/admin/recalculate', methods=['POST'])
def recalculate_points():
    try:
        ScoringService.recalculate_all_match_points()
        flash('Punkte neu berechnet', 'success')
    except Exception as e:
        flash(f'Berechnung fehlgeschlagen: {str(e)}', 'error')
    
    return redirect(url_for('admin.index'))

@admin_bp.route('/admin/calculate-tournament-points', methods=['POST'])
def calculate_tournament_points():
    try:
        result = ScoringService.calculate_tournament_points()
        if result:
            flash('Turnierpunkte berechnet', 'success')
        else:
            flash('Turnier noch nicht beendet - keine Punkte berechnet', 'warning')
    except Exception as e:
        flash(f'Berechnung fehlgeschlagen: {str(e)}', 'error')

    return redirect(url_for('admin.index'))

@admin_bp.route('/admin/phase-locks', methods=['GET', 'POST'])
def phase_locks():
    """Manage betting phase locks."""
    user = get_current_user()

    if request.method == 'POST':
        phase_name = request.form.get('phase_name', '').strip().lower()
        action = request.form.get('action', '')

        if phase_name and action in ['lock', 'unlock']:
            is_locked = (action == 'lock')
            BettingPhaseLock.set_lock(phase_name, is_locked, user.id)
            status = 'gesperrt' if is_locked else 'geöffnet'
            flash(f'{phase_name.title()} wurde {status}', 'success')

        return redirect(url_for('admin.phase_locks'))

    # Get all phase locks
    phase_locks = BettingPhaseLock.get_all_locks()

    return render_template('admin/phase_locks.html',
                          phase_locks=phase_locks,
                          user=user)
