"""
Tournament Management Routes for Admin
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime
from app.models import Tournament, TournamentGroup, TournamentTeam, TournamentRound, User
from app import db

admin_tournaments_bp = Blueprint('admin_tournaments', __name__)


def get_current_user():
    from flask import session
    if 'user_id' not in session:
        return None
    return User.query.get(session['user_id'])


@admin_tournaments_bp.before_request
def check_admin():
    from flask import session, redirect, url_for, flash
    if not session.get('is_admin'):
        flash('Admin-Zugriff erforderlich', 'error')
        return redirect(url_for('auth.login'))


@admin_tournaments_bp.route('/admin/tournaments')
def tournaments():
    """List all tournaments."""
    all_tournaments = Tournament.query.order_by(Tournament.created_at.desc()).all()
    
    # Get user's selected tournament
    user = get_current_user()
    if user and user.selected_tournament_id:
        active_tournament = Tournament.query.get(user.selected_tournament_id)
    else:
        active_tournament = Tournament.query.filter_by(is_active=True).first()
    
    return render_template('admin/tournaments.html',
                          tournaments=all_tournaments,
                          active_tournament=active_tournament,
                          user=user)


@admin_tournaments_bp.route('/admin/tournaments/create', methods=['GET', 'POST'])
def create_tournament():
    """Create a new tournament."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        short_name = request.form.get('short_name', '').strip().lower()
        season = request.form.get('season', type=int)
        league_shortcut = request.form.get('league_shortcut', '').strip()
        num_groups = request.form.get('num_groups', 12, type=int)
        teams_per_group = request.form.get('teams_per_group', 4, type=int)
        
        if not name or not short_name or not season:
            flash('Name, Kurzname und Saison sind erforderlich', 'error')
            return render_template('admin/create_tournament.html')
        
        # Check if short_name is unique
        existing = Tournament.query.filter_by(short_name=short_name).first()
        if existing:
            flash(f'Turnier "{short_name}" existiert bereits', 'error')
            return render_template('admin/create_tournament.html')
        
        # Get provider settings
        provider_type = request.form.get('provider_type', 'openligadb')
        provider_config = {}
        if provider_type == 'openligadb':
            provider_config['league_shortcut'] = request.form.get('league_shortcut', short_name)
            provider_config['season'] = season
        
        tournament = Tournament(
            name=name,
            short_name=short_name,
            season=season,
            league_shortcut=league_shortcut or short_name,
            num_groups=num_groups,
            teams_per_group=teams_per_group,
            provider_type=provider_type,
            provider_config=provider_config if provider_config else None,
            is_active=False  # Don't auto-activate
        )
        db.session.add(tournament)
        db.session.commit()
        
        flash(f'Turnier "{name}" erstellt', 'success')
        return redirect(url_for('admin_tournaments.tournaments'))
    
    return render_template('admin/create_tournament.html', user=get_current_user())


@admin_tournaments_bp.route('/admin/tournaments/<int:tournament_id>')
def tournament_detail(tournament_id):
    """Show tournament details with groups and teams."""
    tournament = Tournament.query.get_or_404(tournament_id)
    groups = TournamentGroup.query.filter_by(tournament_id=tournament_id).order_by(TournamentGroup.order_index).all()
    teams = TournamentTeam.query.filter_by(tournament_id=tournament_id).all()
    rounds = TournamentRound.query.filter_by(tournament_id=tournament_id).order_by(TournamentRound.order_index).all()
    
    # Organize teams by group
    teams_by_group = {}
    for group in groups:
        teams_by_group[group.id] = []
    for team in teams:
        if team.group_id in teams_by_group:
            teams_by_group[team.group_id].append(team)
    
    # Get matches for this tournament
    from app.models import Match
    league_shortcut = tournament.get_league_shortcut() or tournament.short_name
    matches = Match.query.filter_by(league_shortcut=league_shortcut).all()
    
    return render_template('admin/tournament_detail.html',
                          tournament=tournament,
                          groups=groups,
                          teams_by_group=teams_by_group,
                          rounds=rounds,
                          matches=matches,
                          user=get_current_user())


@admin_tournaments_bp.route('/admin/tournaments/<int:tournament_id>/activate', methods=['POST'])
def activate_tournament(tournament_id):
    """Activate a tournament (deactivates others)."""
    Tournament.set_active(tournament_id)
    tournament = Tournament.query.get(tournament_id)
    flash(f'Turnier "{tournament.name}" ist jetzt aktiv', 'success')
    return redirect(url_for('admin_tournaments.tournaments'))


@admin_tournaments_bp.route('/user/select-tournament/<int:tournament_id>', methods=['POST'])
def select_tournament(tournament_id):
    """User selects which tournament to view."""
    from flask import session
    
    user = get_current_user()
    if not user:
        flash('Bitte einloggen', 'error')
        return redirect(url_for('auth.login'))
    
    tournament = Tournament.query.get_or_404(tournament_id)
    user.selected_tournament_id = tournament_id
    db.session.commit()
    
    flash(f'Turnier gewechselt: {tournament.name}', 'success')
    return redirect(request.referrer or url_for('main.dashboard'))


@admin_tournaments_bp.route('/admin/tournaments/<int:tournament_id>/deactivate', methods=['POST'])
def deactivate_tournament(tournament_id):
    """Deactivate (archive) a tournament."""
    tournament = Tournament.query.get_or_404(tournament_id)
    tournament.is_active = False
    db.session.commit()
    flash(f'Turnier "{tournament.name}" archiviert', 'info')
    return redirect(url_for('admin_tournaments.tournaments'))


@admin_tournaments_bp.route('/admin/tournaments/<int:tournament_id>/delete', methods=['POST'])
def delete_tournament(tournament_id):
    """Delete a tournament and all its data."""
    from app.models import TournamentGroup, TournamentTeam, TournamentRound, Match, ScoringConfig
    
    tournament = Tournament.query.get_or_404(tournament_id)
    name = tournament.name
    
    # Delete related data first
    TournamentGroup.query.filter_by(tournament_id=tournament_id).delete()
    TournamentTeam.query.filter_by(tournament_id=tournament_id).delete()
    TournamentRound.query.filter_by(tournament_id=tournament_id).delete()
    ScoringConfig.query.filter_by(tournament_id=tournament_id).delete()
    
    # Delete matches
    league_shortcut = tournament.get_league_shortcut() or tournament.short_name
    Match.query.filter_by(league_shortcut=league_shortcut).delete()
    
    # Delete tournament
    db.session.delete(tournament)
    db.session.commit()
    
    flash(f'Turnier "{name}" und alle zugehörigen Daten gelöscht', 'success')
    return redirect(url_for('admin_tournaments.tournaments'))


@admin_tournaments_bp.route('/admin/tournaments/<int:tournament_id>/results', methods=['GET', 'POST'])
def enter_results(tournament_id):
    """Enter match results for manual tournaments."""
    from app.models import Match
    from app.services.scoring import ScoringService
    
    tournament = Tournament.query.get_or_404(tournament_id)
    
    # Get matches for this tournament
    league_shortcut = tournament.get_league_shortcut() or tournament.short_name
    matches = Match.query.filter_by(league_shortcut=league_shortcut).order_by(Match.match_date).all()
    
    if request.method == 'POST':
        updated = 0
        for match in matches:
            score1_key = f'score_{match.id}_team1'
            score2_key = f'score_{match.id}_team2'
            finished_key = f'finished_{match.id}'
            
            score1 = request.form.get(score1_key, '').strip()
            score2 = request.form.get(score2_key, '').strip()
            is_finished = finished_key in request.form
            
            # Update scores if provided
            if score1 != '' and score2 != '':
                match.team1_score = int(score1)
                match.team2_score = int(score2)
                match.is_finished = is_finished
                
                if is_finished:
                    match.last_updated = datetime.utcnow()
                    updated += 1
        
        db.session.commit()
        
        # Recalculate points for finished matches
        if updated > 0:
            ScoringService.recalculate_all_match_points(tournament_id=tournament.id)
            flash(f'{updated} Spiele aktualisiert und Punkte neu berechnet', 'success')
        else:
            flash('Ergebnisse gespeichert', 'success')
        
        return redirect(url_for('admin_tournaments.enter_results', tournament_id=tournament_id))
    
    return render_template('admin/enter_results.html',
                          tournament=tournament,
                          matches=matches,
                          user=get_current_user())


@admin_tournaments_bp.route('/admin/tournaments/<int:tournament_id>/setup-groups', methods=['GET', 'POST'])
def setup_groups(tournament_id):
    """Setup groups for a tournament."""
    tournament = Tournament.query.get_or_404(tournament_id)
    
    if request.method == 'POST':
        # Clear existing groups
        TournamentGroup.query.filter_by(tournament_id=tournament_id).delete()
        
        # Create new groups
        num_groups = request.form.get('num_groups', tournament.num_groups, type=int)
        group_prefix = request.form.get('group_prefix', 'Gruppe')
        
        for i in range(num_groups):
            code = chr(65 + i)  # A, B, C, ...
            name = f"{group_prefix} {code}"
            group = TournamentGroup(
                tournament_id=tournament_id,
                name=name,
                code=code,
                order_index=i
            )
            db.session.add(group)
        
        db.session.commit()
        flash(f'{num_groups} Gruppen erstellt', 'success')
        return redirect(url_for('admin_tournaments.tournament_detail', tournament_id=tournament_id))
    
    existing_groups = TournamentGroup.query.filter_by(tournament_id=tournament_id).count()
    return render_template('admin/setup_groups.html',
                          tournament=tournament,
                          existing_groups=existing_groups,
                          user=get_current_user())


@admin_tournaments_bp.route('/admin/tournaments/<int:tournament_id>/assign-teams', methods=['GET', 'POST'])
def assign_teams(tournament_id):
    """Assign teams to groups."""
    tournament = Tournament.query.get_or_404(tournament_id)
    groups = TournamentGroup.query.filter_by(tournament_id=tournament_id).order_by(TournamentGroup.order_index).all()
    
    # Get available teams from matches or manual input
    from app.services.teams import get_sorted_unique_teams
    available_teams = get_sorted_unique_teams()
    
    if request.method == 'POST':
        # Clear existing team assignments
        TournamentTeam.query.filter_by(tournament_id=tournament_id).delete()
        
        # Process form data - teams are submitted as team_0, team_1, etc.
        team_index = 0
        while True:
            team_name = request.form.get(f'team_{team_index}')
            if team_name is None:
                break
            
            team_name = team_name.strip()
            if team_name:
                # Get group selection
                group_code = request.form.get(f'group_for_{team_index}')
                group = next((g for g in groups if g.code == group_code), None)
                
                # Find team_id from available teams
                team_id = next((tid for tname, tid in available_teams if tname == team_name), None)
                
                tournament_team = TournamentTeam(
                    tournament_id=tournament_id,
                    group_id=group.id if group else None,
                    team_name=team_name,
                    team_id=team_id
                )
                db.session.add(tournament_team)
            
            team_index += 1
        
        db.session.commit()
        flash('Teams zugewiesen', 'success')
        return redirect(url_for('admin_tournaments.tournament_detail', tournament_id=tournament_id))
    
    # Get existing assignments
    existing_teams = TournamentTeam.query.filter_by(tournament_id=tournament_id).all()
    
    return render_template('admin/assign_teams.html',
                          tournament=tournament,
                          groups=groups,
                          available_teams=available_teams,
                          existing_teams=existing_teams,
                          user=get_current_user())


@admin_tournaments_bp.route('/admin/tournaments/<int:tournament_id>/generate-matches', methods=['POST'])
def generate_group_matches(tournament_id):
    """Generate all group stage matches (round-robin) for manual tournaments."""
    from app.models import Tournament, TournamentGroup, TournamentTeam, Match
    from app import db
    from datetime import datetime, timedelta
    
    tournament = Tournament.query.get_or_404(tournament_id)
    
    # Only for manual provider tournaments
    if tournament.provider_type != 'manual':
        flash('Gruppenspiele können nur für manuelle Turniere generiert werden', 'error')
        return redirect(url_for('admin_tournaments.tournament_detail', tournament_id=tournament_id))
    
    # Get all groups with their teams
    groups = TournamentGroup.query.filter_by(tournament_id=tournament_id).all()
    
    generated = 0
    base_date = datetime.now().replace(hour=15, minute=0, second=0, microsecond=0)
    
    for group in groups:
        # Get teams in this group
        teams = TournamentTeam.query.filter_by(group_id=group.id).all()
        team_names = [tt.team_name for tt in teams]
        
        if len(team_names) < 2:
            continue
        
        # Generate round-robin matches (everyone plays everyone once)
        match_counter = 0
        for i in range(len(team_names)):
            for j in range(i + 1, len(team_names)):
                # Check if match already exists
                existing = Match.query.filter(
                    ((Match.team1_name == team_names[i]) & (Match.team2_name == team_names[j])) |
                    ((Match.team1_name == team_names[j]) & (Match.team2_name == team_names[i]))
                ).filter_by(league_shortcut=tournament.get_league_shortcut()).first()
                
                if not existing:
                    match = Match(
                        match_id=int(datetime.now().timestamp()) + generated,  # Unique ID
                        league_shortcut=tournament.get_league_shortcut() or tournament.short_name,
                        league_season=int(tournament.season),
                        round_name=group.name,
                        round_type='group',
                        group_order_id=group.id,
                        team1_id=0,  # Will be updated later
                        team1_name=team_names[i],
                        team1_short=team_names[i][:3].upper(),
                        team2_id=0,
                        team2_name=team_names[j],
                        team2_short=team_names[j][:3].upper(),
                        match_date=base_date + timedelta(days=generated, hours=match_counter % 3),
                        is_finished=False
                    )
                    db.session.add(match)
                    generated += 1
                    match_counter += 1
    
    db.session.commit()
    flash(f'{generated} Gruppenspiele generiert. Du kannst jetzt Datum/Uhrzeit bearbeiten.', 'success')
    return redirect(url_for('admin_tournaments.tournament_detail', tournament_id=tournament_id))


@admin_tournaments_bp.route('/admin/tournaments/<int:tournament_id>/add-match', methods=['GET', 'POST'])
def add_manual_match(tournament_id):
    """Add a single match manually (for knockout or special matches)."""
    from app.models import Tournament, TournamentGroup, TournamentTeam, Match
    from app import db
    from datetime import datetime
    
    tournament = Tournament.query.get_or_404(tournament_id)
    groups = TournamentGroup.query.filter_by(tournament_id=tournament_id).all()
    teams = TournamentTeam.query.filter_by(tournament_id=tournament_id).all()
    
    if request.method == 'POST':
        team1_name = request.form.get('team1_name')
        team2_name = request.form.get('team2_name')
        round_name = request.form.get('round_name')
        round_type = request.form.get('round_type', 'knockout')
        match_date_str = request.form.get('match_date')
        match_time_str = request.form.get('match_time')
        
        if not all([team1_name, team2_name, round_name, match_date_str]):
            flash('Alle Pflichtfelder ausfüllen', 'error')
            return redirect(url_for('admin_tournaments.add_manual_match', tournament_id=tournament_id))
        
        # Parse date and time
        try:
            match_date = datetime.strptime(match_date_str, '%Y-%m-%d')
            if match_time_str:
                time_parts = match_time_str.split(':')
                match_date = match_date.replace(hour=int(time_parts[0]), minute=int(time_parts[1]))
        except ValueError:
            flash('Ungültiges Datum oder Uhrzeit', 'error')
            return redirect(url_for('admin_tournaments.add_manual_match', tournament_id=tournament_id))
        
        # Create match
        match = Match(
            match_id=int(datetime.now().timestamp()),
            league_shortcut=tournament.get_league_shortcut() or tournament.short_name,
            league_season=int(tournament.season),
            round_name=round_name,
            round_type=round_type,
            group_order_id=0,  # KO matches don't need group ordering
            team1_id=0,
            team1_name=team1_name,
            team1_short=team1_name[:3].upper(),
            team2_id=0,
            team2_name=team2_name,
            team2_short=team2_name[:3].upper(),
            match_date=match_date,
            is_finished=False
        )
        db.session.add(match)
        db.session.commit()
        
        flash(f'Spiel {team1_name} vs {team2_name} erstellt', 'success')
        return redirect(url_for('admin_tournaments.tournament_detail', tournament_id=tournament_id))
    
    return render_template('admin/add_match.html',
                          tournament=tournament,
                          groups=groups,
                          teams=teams,
                          user=get_current_user())


@admin_tournaments_bp.route('/admin/matches/<int:match_id>/edit', methods=['GET', 'POST'])
def edit_match(match_id):
    """Edit match details (date, time, location) for manual tournaments."""
    from app.models import Match, Tournament, TournamentGroup, TournamentTeam
    from app import db
    from datetime import datetime
    
    match = Match.query.get_or_404(match_id)
    
    # Get tournament for this match (SQLite-compatible JSON query)
    tournament = Tournament.query.filter_by(
        short_name=match.league_shortcut
    ).first()
    
    if not tournament:
        # For SQLite, we need to check JSON in Python
        all_tournaments = Tournament.query.all()
        for t in all_tournaments:
            if t.provider_config and t.provider_config.get('league_shortcut') == match.league_shortcut:
                tournament = t
                break
    
    if not tournament or tournament.provider_type != 'manual':
        flash('Spiele können nur für manuelle Turniere bearbeitet werden', 'error')
        return redirect(url_for('admin.edit_groups'))
    
    if request.method == 'POST':
        match_date_str = request.form.get('match_date')
        match_time_str = request.form.get('match_time')
        location = request.form.get('location', '')
        
        try:
            if match_date_str:
                new_date = datetime.strptime(match_date_str, '%Y-%m-%d')
                if match_time_str:
                    time_parts = match_time_str.split(':')
                    new_date = new_date.replace(hour=int(time_parts[0]), minute=int(time_parts[1]))
                else:
                    new_date = new_date.replace(hour=match.match_date.hour, minute=match.match_date.minute)
                match.match_date = new_date
            
            match.location = location
            db.session.commit()
            
            flash(f'Spiel aktualisiert: {match.team1_name} vs {match.team2_name}', 'success')
            return redirect(url_for('admin.edit_groups'))
            
        except ValueError as e:
            flash(f'Ungültiges Datum/Uhrzeit: {str(e)}', 'error')
    
    return render_template('admin/edit_match.html',
                          match=match,
                          tournament=tournament,
                          user=get_current_user())
