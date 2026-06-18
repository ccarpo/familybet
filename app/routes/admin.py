from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import User, Match, Bet, ScoringConfig, BettingPhaseLock, Tournament, TournamentGroup, TournamentTeam, TournamentRound
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
    
    # Get all users (sorted alphabetically)
    from app.services.users import get_sorted_users
    users = get_sorted_users(include_hidden=True)
    
    # Get current user's selected tournament for scoring config
    from app.models import Tournament
    user = get_current_user()
    if user and user.selected_tournament_id:
        active_tournament = Tournament.query.get(user.selected_tournament_id)
    else:
        active_tournament = Tournament.query.filter_by(is_active=True).first()
    scoring_config = ScoringConfig.get_current(
        tournament_id=active_tournament.id if active_tournament else None
    )
    
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
        points_champion = int(request.form.get('points_champion', 10))
        points_finalist = int(request.form.get('points_finalist', 5))
        points_semifinalist = int(request.form.get('points_semifinalist', 3))
        
        # Validate inputs
        if any(p < 0 for p in [points_exact, points_diff, points_winner, points_champion, points_finalist, points_semifinalist]):
            flash('Punkte können nicht negativ sein', 'error')
            return redirect(url_for('admin.index'))
        
        # Get current user's selected tournament for scoring config
        from app.models import Tournament
        user = get_current_user()
        if user and user.selected_tournament_id:
            active_tournament = Tournament.query.get(user.selected_tournament_id)
        else:
            active_tournament = Tournament.query.filter_by(is_active=True).first()
        tournament_id = active_tournament.id if active_tournament else None
        
        # Create new config for this tournament with extra points
        ScoringConfig.create_new(
            points_exact=points_exact,
            points_diff=points_diff,
            points_winner=points_winner,
            points_champion=points_champion,
            points_finalist=points_finalist,
            points_semifinalist=points_semifinalist,
            tournament_id=tournament_id
        )
        
        # Recalculate match points with new config (for this tournament)
        ScoringService.recalculate_all_match_points(tournament_id=tournament_id)
        
        flash(f'Punktesystem aktualisiert: Exakt={points_exact}, Diff={points_diff}, Sieger={points_winner}, Champion={points_champion}. Match-Punkte neu berechnet. Turnierpunkte separat berechnen (Button "Turnierpunkte berechnen").', 'success')
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
        from app.services.users import email_exists
        if email_exists(email):
            flash('Email wird bereits verwendet', 'error')
            return redirect(url_for('admin.index'))
    
    new_user = User(name=name, email=email, is_admin=is_admin_user)
    db.session.add(new_user)
    db.session.commit()
    
    # Send welcome email if enabled
    if email:
        from app.services.email_service import send_welcome_email
        send_welcome_email(new_user)
    
    flash(f'Benutzer {name} erstellt', 'success')
    return redirect(url_for('admin.index'))

@admin_bp.route('/admin/assign-groups', methods=['POST'])
def assign_groups():
    """Assign teams to matches based on Tournament data"""
    from app.models import Tournament, TournamentGroup, TournamentTeam, Match
    
    try:
        # Get user's selected tournament
        user = get_current_user()
        if user and user.selected_tournament_id:
            active_tournament = Tournament.query.get(user.selected_tournament_id)
        else:
            active_tournament = Tournament.query.filter_by(is_active=True).first()
        if not active_tournament:
            flash('Kein aktives Turnier vorhanden', 'error')
            return redirect(url_for('admin.check_data'))
        
        # Get all tournament teams with their groups
        tournament_teams = TournamentTeam.query.filter_by(
            tournament_id=active_tournament.id
        ).all()
        
        # Build team -> group mapping
        team_to_group = {}
        for tt in tournament_teams:
            if tt.group:
                team_to_group[tt.team_name] = tt.group.name
        
        # Get all matches for this tournament's league
        league_shortcut = active_tournament.get_league_shortcut()
        if league_shortcut:
            matches = Match.query.filter_by(
                league_shortcut=league_shortcut
            ).all()
        else:
            matches = Match.query.all()
        
        # Assign group to each match based on team assignments
        assigned_count = 0
        for match in matches:
            # Check if team1 has a group assignment
            if match.team1_name in team_to_group:
                match.round_name = team_to_group[match.team1_name]
                assigned_count += 1
            # Check if team2 has a group assignment
            elif match.team2_name in team_to_group:
                match.round_name = team_to_group[match.team2_name]
                assigned_count += 1
        
        db.session.commit()
        flash(f'{assigned_count} Spiele wurden den Gruppen zugeordnet ({active_tournament.name})', 'success')
    except Exception as e:
        flash(f'Fehler bei Gruppenzuordnung: {str(e)}', 'error')
    
    return redirect(url_for('admin.edit_groups'))

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
    from app.models import Match, Tournament, TournamentGroup, TournamentTeam
    from collections import defaultdict
    
    if request.method == 'POST':
        action = request.form.get('action', '')
        
        if action == 'move_team':
            # Move team to new group
            team_name = request.form.get('team_name', '').strip()
            new_group = request.form.get('new_group', '').strip()
            
            if team_name and new_group:
                # Get user's selected tournament
                user = get_current_user()
                if user and user.selected_tournament_id:
                    active_tournament = Tournament.query.get(user.selected_tournament_id)
                else:
                    active_tournament = Tournament.query.filter_by(is_active=True).first()
                if not active_tournament:
                    flash('Kein aktives Turnier vorhanden', 'error')
                    return redirect(url_for('admin.edit_groups'))
                
                # Find the new group
                new_group_obj = TournamentGroup.query.filter_by(
                    tournament_id=active_tournament.id,
                    name=new_group
                ).first()
                
                if not new_group_obj:
                    flash(f'Gruppe {new_group} nicht gefunden', 'error')
                    return redirect(url_for('admin.edit_groups'))
                
                # Update TournamentTeam assignment
                tournament_team = TournamentTeam.query.filter_by(
                    tournament_id=active_tournament.id,
                    team_name=team_name
                ).first()
                
                if tournament_team:
                    tournament_team.group_id = new_group_obj.id
                
                # Update all matches for this team
                matches = Match.query.filter(
                    db.or_(
                        Match.team1_name == team_name,
                        Match.team2_name == team_name
                    )
                ).all()
                
                match_count = 0
                for match in matches:
                    # Only update group stage matches (not knockout)
                    # round_type='group' OR (round_type is None AND round_name contains 'Gruppe' - legacy data)
                    is_group_match = match.round_type == 'group' or (match.round_type is None and 'Gruppe' in match.round_name)
                    if is_group_match and match.round_name != new_group:
                        match.round_name = new_group
                        match_count += 1
                
                db.session.commit()
                flash(f'Team {team_name} wurde nach {new_group} verschoben', 'success')
        
        return redirect(url_for('admin.edit_groups'))
    
    # Get user's selected tournament
    user = get_current_user()
    if user and user.selected_tournament_id:
        active_tournament = Tournament.query.get(user.selected_tournament_id)
    else:
        active_tournament = Tournament.query.filter_by(is_active=True).first()
    if not active_tournament:
        flash('Kein aktives Turnier vorhanden', 'error')
        return redirect(url_for('admin.index'))
    
    # Get groups from tournament data
    tournament_groups = TournamentGroup.query.filter_by(
        tournament_id=active_tournament.id
    ).order_by(TournamentGroup.order_index).all()
    
    # Build groups dict from TournamentTeam assignments
    groups = defaultdict(list)
    unassigned = []
    
    for group in tournament_groups:
        teams_in_group = TournamentTeam.query.filter_by(
            tournament_id=active_tournament.id,
            group_id=group.id
        ).all()
        for team in teams_in_group:
            groups[group.name].append(team.team_name)
    
    # Find unassigned teams (teams in tournament but not in any group)
    all_tournament_teams = TournamentTeam.query.filter_by(
        tournament_id=active_tournament.id
    ).all()
    assigned_team_names = set()
    for group_teams in groups.values():
        assigned_team_names.update(group_teams)
    
    for team in all_tournament_teams:
        if team.team_name not in assigned_team_names:
            unassigned.append(team.team_name)
    
    # Build teams_data for template compatibility
    teams_data = defaultdict(lambda: {'group': 'Unknown', 'matches': []})
    for group_name, team_names in groups.items():
        for team_name in team_names:
            teams_data[team_name]['group'] = group_name
    for team_name in unassigned:
        teams_data[team_name]['group'] = 'Unknown'
    
    # Get matches for each group from Match table
    group_matches = {}
    league_shortcut = active_tournament.get_league_shortcut()
    for group in tournament_groups:
        if league_shortcut:
            group_matches[group.name] = Match.query.filter_by(
                round_name=group.name,
                league_shortcut=league_shortcut
            ).order_by(Match.match_date).all()
        else:
            group_matches[group.name] = Match.query.filter_by(
                round_name=group.name
            ).order_by(Match.match_date).all()
    
    return render_template('admin/edit_groups.html', 
                          tournament=active_tournament,
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
            from app.services.users import email_exists
            if email_exists(email, exclude_user_id=user_id):
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
    """Sync matches using the active tournament's configured provider."""
    from app.services.providers import ProviderFactory, DataProvider
    
    try:
        # Get user's selected tournament
        user = get_current_user()
        if user and user.selected_tournament_id:
            active_tournament = Tournament.query.get(user.selected_tournament_id)
        else:
            active_tournament = Tournament.query.filter_by(is_active=True).first()
        if not active_tournament:
            flash('Kein aktives Turnier vorhanden', 'error')
            return redirect(url_for('admin.index'))
        
        # Check provider type
        if active_tournament.provider_type == 'manual':
            flash('Manuelle Turniere haben keine automatische Synchronisation. Bitte Spiele manuell erstellen oder CSV importieren.', 'warning')
            return redirect(url_for('admin.index'))
        
        # Get provider for this tournament
        provider = ProviderFactory.get(
            active_tournament.provider_type or 'openligadb',
            active_tournament.provider_config or {}
        )
        
        # Get league shortcut and season
        league_shortcut = active_tournament.get_league_shortcut()
        season = active_tournament.get_provider_season()
        
        if not league_shortcut:
            flash('Kein league_shortcut für dieses Turnier konfiguriert', 'error')
            return redirect(url_for('admin.index'))
        
        # Fetch matches from provider
        matches_data = provider.fetch_matches(league_shortcut, season)
        
        if not matches_data:
            flash('Keine neuen Spiele gefunden oder Fehler beim Abrufen', 'warning')
            return redirect(url_for('admin.index'))
        
        # Import matches (using existing logic from openligadb service)
        synced = _import_matches_from_provider(matches_data, league_shortcut, season)
        
        # Update tournament stats from imported data (for OpenLigaDB)
        if synced > 0 and active_tournament.provider_type == 'openligadb':
            _update_tournament_stats_from_matches(active_tournament, matches_data)
            flash(f'Turnier-Statistiken aktualisiert: {active_tournament.num_groups} Gruppen mit ~{active_tournament.teams_per_group} Teams', 'info')
        
        flash(f'{synced} Spiele von {provider.provider_name} synchronisiert', 'success')
    except ValueError as e:
        flash(f'Provider-Fehler: {str(e)}', 'error')
    except Exception as e:
        flash(f'Synchronisation fehlgeschlagen: {str(e)}', 'error')
    
    return redirect(url_for('admin.index'))


def _import_matches_from_provider(matches_data, league_shortcut, season):
    """Import matches from provider data into database."""
    from app.services.openligadb import OpenLigaDBClient
    
    # Reuse existing sync logic
    service = OpenLigaDBClient()
    
    # Override fetch to use our already-fetched data
    service.get_match_data = lambda s, l: [m.to_dict() for m in matches_data]
    
    return service.sync_matches(league_shortcut, season)


def _update_tournament_stats_from_matches(tournament, matches_data):
    """
    Update tournament stats (num_groups, teams_per_group) from imported matches.
    This is called after OpenLigaDB sync to reflect actual data.
    """
    # Count unique group names from group stage matches
    group_names = set()
    teams_per_group_count = {}
    
    for match in matches_data:
        round_type = match.round_type
        round_name = match.round_name
        
        # Only consider group stage matches
        if round_type == 'group' or (round_type is None and 'Gruppe' in round_name):
            group_names.add(round_name)
            
            # Count teams per group
            if round_name not in teams_per_group_count:
                teams_per_group_count[round_name] = set()
            teams_per_group_count[round_name].add(match.team1_name)
            teams_per_group_count[round_name].add(match.team2_name)
    
    # Update tournament with actual stats
    if group_names:
        tournament.num_groups = len(group_names)
        # Use max teams per group as reference
        max_teams = max(len(teams) for teams in teams_per_group_count.values()) if teams_per_group_count else 4
        tournament.teams_per_group = max_teams
        
        from app import db
        db.session.commit()
        
        print(f"[Tournament Stats] Updated {tournament.name}: {len(group_names)} groups, ~{max_teams} teams/group")

@admin_bp.route('/admin/recalculate', methods=['POST'])
def recalculate_points():
    try:
        # Get user's selected tournament for recalculation
        user = get_current_user()
        if user and user.selected_tournament_id:
            active_tournament = Tournament.query.get(user.selected_tournament_id)
        else:
            active_tournament = Tournament.query.filter_by(is_active=True).first()
        tournament_id = active_tournament.id if active_tournament else None
        
        ScoringService.recalculate_all_match_points(tournament_id=tournament_id)
        flash('Match-Punkte neu berechnet' + (f' für {active_tournament.name}' if active_tournament else ''), 'success')
    except Exception as e:
        flash(f'Berechnung fehlgeschlagen: {str(e)}', 'error')
    
    return redirect(url_for('admin.index'))

@admin_bp.route('/admin/calculate-tournament-points', methods=['POST'])
def calculate_tournament_points():
    try:
        # Get user's selected tournament
        user = get_current_user()
        if user and user.selected_tournament_id:
            active_tournament = Tournament.query.get(user.selected_tournament_id)
        else:
            active_tournament = Tournament.query.filter_by(is_active=True).first()
        tournament_id = active_tournament.id if active_tournament else None
        
        result = ScoringService.calculate_tournament_points(tournament_id=tournament_id)
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


@admin_bp.route('/admin/email', methods=['GET', 'POST'])
def email_settings():
    """Email settings and test email."""
    from flask import current_app
    from app.models import EmailSettings
    user = get_current_user()
    settings = EmailSettings.get()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'save':
            settings.enabled = 'enabled' in request.form
            settings.send_magic_link = 'send_magic_link' in request.form
            settings.send_welcome = 'send_welcome' in request.form
            settings.send_deadline_24h = 'send_deadline_24h' in request.form
            settings.send_deadline_2h = 'send_deadline_2h' in request.form
            settings.send_match_result = 'send_match_result' in request.form
            db.session.commit()
            flash('Email-Einstellungen gespeichert', 'success')

        elif action == 'test':
            to_email = request.form.get('to_email', '').strip()
            if not to_email:
                flash('Bitte Email-Adresse angeben', 'error')
            else:
                from app.services.email_service import send_test_email
                ok = send_test_email(to_email, user.name)
                if ok:
                    flash(f'Test-Email an {to_email} gesendet ✓', 'success')
                elif not settings.enabled:
                    flash('Email ist global deaktiviert. Aktiviere Email oben.', 'warning')
                else:
                    flash('Email-Versand fehlgeschlagen. SMTP-Konfiguration prüfen.', 'error')

        return redirect(url_for('admin.email_settings'))

    mail_config = {
        'server': current_app.config.get('MAIL_SERVER', ''),
        'port': current_app.config.get('MAIL_PORT', 587),
        'username': current_app.config.get('MAIL_USERNAME', ''),
        'sender': current_app.config.get('MAIL_DEFAULT_SENDER', ''),
    }

    users_with_email = User.query.filter(
        User.email.isnot(None),
        User.email_notifications == True
    ).count()

    return render_template('admin/email_settings.html',
                           user=user,
                           settings=settings,
                           mail_config=mail_config,
                           users_with_email=users_with_email)
