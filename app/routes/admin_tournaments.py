"""
Tournament Management Routes for Admin
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
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
    active_tournament = Tournament.get_active()
    return render_template('admin/tournaments.html',
                          tournaments=all_tournaments,
                          active_tournament=active_tournament,
                          user=get_current_user())


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
        
        tournament = Tournament(
            name=name,
            short_name=short_name,
            season=season,
            league_shortcut=league_shortcut or short_name,
            num_groups=num_groups,
            teams_per_group=teams_per_group,
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
            teams_by_group[group.id].append(team)
    
    return render_template('admin/tournament_detail.html',
                          tournament=tournament,
                          groups=groups,
                          teams_by_group=teams_by_group,
                          rounds=rounds,
                          user=get_current_user())


@admin_tournaments_bp.route('/admin/tournaments/<int:tournament_id>/activate', methods=['POST'])
def activate_tournament(tournament_id):
    """Activate a tournament (deactivates others)."""
    Tournament.set_active(tournament_id)
    tournament = Tournament.query.get(tournament_id)
    flash(f'Turnier "{tournament.name}" ist jetzt aktiv', 'success')
    return redirect(url_for('admin_tournaments.tournaments'))
