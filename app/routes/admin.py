from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import User, Match, Bet
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
    
    return render_template('admin/index.html',
                          user=user,
                          stats={
                              'total_users': total_users,
                              'total_matches': total_matches,
                              'finished_matches': finished_matches,
                              'total_bets': total_bets
                          },
                          users=users)

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

@admin_bp.route('/admin/users/<int:user_id>')
def user_bets(user_id):
    user = get_current_user()
    target_user = User.query.get_or_404(user_id)
    
    # Get all matches
    all_matches = Match.query.order_by(Match.match_date).all()
    
    # Get user's bets
    user_bets = {bet.match_id: bet for bet in Bet.query.filter_by(user_id=user_id).all()}
    
    return render_template('admin/user_bets.html',
                          user=user,
                          target_user=target_user,
                          matches=all_matches,
                          user_bets=user_bets)

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
