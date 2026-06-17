from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from app import db
import secrets


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_hidden_from_leaderboard = db.Column(db.Boolean, default=False)
    magic_token = db.Column(db.String(64), unique=True, nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    bets = db.relationship('Bet', backref='user', lazy=True, cascade='all, delete-orphan')
    tournament_bet = db.relationship('TournamentBet', backref='user', lazy=True, uselist=False, cascade='all, delete-orphan')
    
    def generate_magic_token(self):
        self.magic_token = secrets.token_urlsafe(32)
        self.token_expires_at = datetime.utcnow() + timedelta(hours=24)
        return self.magic_token
    
    def is_token_valid(self):
        if not self.token_expires_at:
            return False
        return datetime.utcnow() < self.token_expires_at
    
    def get_total_points(self):
        match_points = db.session.query(db.func.sum(Bet.points_earned)).filter(Bet.user_id == self.id).scalar() or 0
        tournament_points = 0
        if self.tournament_bet:
            tournament_points = self.tournament_bet.points_earned or 0
        return match_points + tournament_points
    
    def __repr__(self):
        return f'<User {self.name}>'


class Match(db.Model):
    __tablename__ = 'matches'
    
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, unique=True, nullable=False)  # OpenLigaDB match ID
    league_shortcut = db.Column(db.String(50), nullable=False)
    league_season = db.Column(db.Integer, nullable=False)
    
    # Round/Group info
    round_name = db.Column(db.String(100), nullable=False)  # e.g., "Gruppe A", "Achtelfinale"
    group_order_id = db.Column(db.Integer, nullable=False)  # OpenLigaDB group order
    
    # Teams
    team1_id = db.Column(db.Integer, nullable=False)
    team1_name = db.Column(db.String(100), nullable=False)
    team1_short = db.Column(db.String(10), nullable=True)
    team2_id = db.Column(db.Integer, nullable=False)
    team2_name = db.Column(db.String(100), nullable=False)
    team2_short = db.Column(db.String(10), nullable=True)
    
    # Match details
    match_date = db.Column(db.DateTime, nullable=False)
    match_date_utc = db.Column(db.DateTime, nullable=True)
    
    # Results
    team1_score = db.Column(db.Integer, nullable=True)
    team2_score = db.Column(db.Integer, nullable=True)
    is_finished = db.Column(db.Boolean, default=False)
    
    # Metadata
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    bets = db.relationship('Bet', backref='match', lazy=True, cascade='all, delete-orphan')
    
    def is_knockout(self):
        knockout_rounds = ['achtelfinale', 'viertelfinale', 'halbfinale', 'finale', 'spiel um platz 3']
        return any(round_name in self.round_name.lower() for round_name in knockout_rounds)
    
    def has_started(self):
        return datetime.utcnow() >= self.match_date
    
    def can_place_bet(self):
        return not self.has_started()

    def is_phase_locked(self):
        """Check if betting is locked for this match's phase."""
        from app.models import BettingPhaseLock

        # Determine phase from round_name
        round_lower = self.round_name.lower()

        if 'gruppe' in round_lower:
            return BettingPhaseLock.is_phase_locked('gruppenphase')
        elif 'sechzehntel' in round_lower or '16' in round_lower:
            return BettingPhaseLock.is_phase_locked('sechzehntelfinale')
        elif 'achtel' in round_lower or '8' in round_lower:
            return BettingPhaseLock.is_phase_locked('achtelfinale')
        elif 'viertel' in round_lower or '4' in round_lower:
            return BettingPhaseLock.is_phase_locked('viertelfinale')
        elif 'halb' in round_lower or 'semi' in round_lower:
            return BettingPhaseLock.is_phase_locked('halbfinale')
        elif 'finale' in round_lower or 'platz 3' in round_lower:
            return BettingPhaseLock.is_phase_locked('finale')

        return False
    
    def get_winner_id(self):
        if not self.is_finished or self.team1_score is None or self.team2_score is None:
            return None
        if self.team1_score > self.team2_score:
            return self.team1_id
        elif self.team2_score > self.team1_score:
            return self.team2_id
        return None  # Draw
    
    def __repr__(self):
        return f'<Match {self.team1_name} vs {self.team2_name}>'


class Bet(db.Model):
    __tablename__ = 'bets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False)
    
    # Predictions
    team1_score_pred = db.Column(db.Integer, nullable=False)
    team2_score_pred = db.Column(db.Integer, nullable=False)
    
    # Scoring
    points_earned = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint: one bet per user per match
    __table_args__ = (db.UniqueConstraint('user_id', 'match_id', name='unique_user_match_bet'),)
    
    def calculate_points(self, actual_team1_score, actual_team2_score):
        if actual_team1_score is None or actual_team2_score is None:
            return 0
        
        # Get current scoring config
        from app.models import ScoringConfig
        config = ScoringConfig.get_current()
        
        pred_diff = self.team1_score_pred - self.team2_score_pred
        actual_diff = actual_team1_score - actual_team2_score
        
        # Exact match
        if self.team1_score_pred == actual_team1_score and self.team2_score_pred == actual_team2_score:
            return config.points_exact
        
        # Correct goal difference
        if pred_diff == actual_diff:
            return config.points_diff
        
        # Correct winner/draw
        pred_winner = 0 if pred_diff == 0 else (1 if pred_diff > 0 else -1)
        actual_winner = 0 if actual_diff == 0 else (1 if actual_diff > 0 else -1)
        if pred_winner == actual_winner:
            return config.points_winner
        
        return 0
    
    def __repr__(self):
        return f'<Bet {self.user.name}: {self.team1_score_pred}-{self.team2_score_pred}>'


class TournamentBet(db.Model):
    __tablename__ = 'tournament_bets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    
    # Tournament winner prediction (entered before tournament starts)
    winner_team_id = db.Column(db.Integer, nullable=True)
    winner_team_name = db.Column(db.String(100), nullable=True)
    
    # 3 other semifinalists (not the winner)
    semifinalist1_id = db.Column(db.Integer, nullable=True)
    semifinalist1_name = db.Column(db.String(100), nullable=True)
    semifinalist2_id = db.Column(db.Integer, nullable=True)
    semifinalist2_name = db.Column(db.String(100), nullable=True)
    semifinalist3_id = db.Column(db.Integer, nullable=True)
    semifinalist3_name = db.Column(db.String(100), nullable=True)
    
    # Scoring (calculated after tournament ends)
    points_earned = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<TournamentBet {self.user.name}: Winner={self.winner_team_name}>'


class ScoringConfig(db.Model):
    """Configurable scoring system for match bets"""
    __tablename__ = 'scoring_config'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Points for each prediction type
    points_exact = db.Column(db.Integer, default=3)    # Exact score prediction
    points_diff = db.Column(db.Integer, default=2)     # Correct goal difference
    points_winner = db.Column(db.Integer, default=1)    # Correct winner/draw
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get_current():
        """Get the current active scoring config, or create default if none exists"""
        config = ScoringConfig.query.filter_by(is_active=True).first()
        if not config:
            # Create default config
            config = ScoringConfig(
                points_exact=3,
                points_diff=2,
                points_winner=1,
                is_active=True
            )
            db.session.add(config)
            db.session.commit()
        return config
    
    @staticmethod
    def create_new(points_exact, points_diff, points_winner):
        """Create a new scoring config and deactivate old ones"""
        # Deactivate all existing configs
        ScoringConfig.query.update({'is_active': False})
        
        # Create new active config
        new_config = ScoringConfig(
            points_exact=points_exact,
            points_diff=points_diff,
            points_winner=points_winner,
            is_active=True
        )
        db.session.add(new_config)
        db.session.commit()
        return new_config
    
    def __repr__(self):
        return f'<ScoringConfig Exact={self.points_exact}, Diff={self.points_diff}, Winner={self.points_winner}>'


class BettingPhaseLock(db.Model):
    """Stores which betting phases are locked (closed for betting)."""
    __tablename__ = 'betting_phase_locks'

    id = db.Column(db.Integer, primary_key=True)
    phase_name = db.Column(db.String(50), unique=True, nullable=False)
    is_locked = db.Column(db.Boolean, default=False)
    locked_at = db.Column(db.DateTime, nullable=True)
    locked_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Phase definitions
    PHASES = [
        ('gruppenphase', 'Gruppenphase'),
        ('sechzehntelfinale', 'Sechzehntelfinale'),
        ('achtelfinale', 'Achtelfinale'),
        ('viertelfinale', 'Viertelfinale'),
        ('halbfinale', 'Halbfinale'),
        ('finale', 'Finale / Spiel um Platz 3'),
    ]

    @classmethod
    def get_or_create(cls, phase_name):
        lock = cls.query.filter_by(phase_name=phase_name).first()
        if not lock:
            lock = cls(phase_name=phase_name, is_locked=False)
            db.session.add(lock)
            db.session.commit()
        return lock

    @classmethod
    def is_phase_locked(cls, phase_name):
        """Check if a specific phase is locked."""
        lock = cls.query.filter_by(phase_name=phase_name.lower()).first()
        return lock.is_locked if lock else False

    @classmethod
    def get_all_locks(cls):
        """Get all phase locks, creating defaults if needed."""
        locks = {}
        for phase_key, phase_label in cls.PHASES:
            lock = cls.get_or_create(phase_key)
            locks[phase_key] = {
                'label': phase_label,
                'is_locked': lock.is_locked,
                'locked_at': lock.locked_at,
                'updated_at': lock.updated_at
            }
        return locks

    @classmethod
    def set_lock(cls, phase_name, locked, user_id=None):
        """Set lock status for a phase."""
        lock = cls.get_or_create(phase_name.lower())
        lock.is_locked = locked
        if locked:
            lock.locked_at = datetime.utcnow()
            lock.locked_by = user_id
        else:
            lock.locked_at = None
            lock.locked_by = None
        db.session.commit()
        return lock

    def __repr__(self):
        return f'<BettingPhaseLock {self.phase_name}: {"locked" if self.is_locked else "open"}>'
