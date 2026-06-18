from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from config import Config

db = SQLAlchemy()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    mail.init_app(app)
    
    with app.app_context():
        # Import models to ensure they are registered
        from app.models import User, Match, Bet, TournamentBet, ScoringConfig

        # Create tables
        db.create_all()

        # Run automatic migrations
        from app.services.migrations import check_and_run_migrations
        check_and_run_migrations()

        # Register blueprints
        from app.routes.auth import auth_bp
        from app.routes.main import main_bp
        from app.routes.bets import bets_bp
        from app.routes.admin import admin_bp
        from app.routes.admin_tournaments import admin_tournaments_bp
        from app.routes.api import api_bp
        
        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)
        app.register_blueprint(bets_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(admin_tournaments_bp)
        app.register_blueprint(api_bp, url_prefix='/api')
        
        # Initialize scheduler
        from app.services.scheduler import init_scheduler
        init_scheduler(app)
        
        # Context processor for tournament globals
        @app.context_processor
        def inject_tournament_globals():
            from flask import session
            from app.models import Tournament, User
            
            try:
                active_tournaments = Tournament.query.filter_by(is_active=True).order_by(Tournament.name).all()
            except Exception:
                active_tournaments = []
            
            context = {'active_tournaments': active_tournaments, 'user_selected_tournament': None}
            
            # Get user's selected tournament
            if session.get('user_id'):
                try:
                    user = User.query.get(session['user_id'])
                    if user and user.selected_tournament_id:
                        selected = Tournament.query.get(user.selected_tournament_id)
                        # Ensure selected tournament is still active
                        if selected and selected.is_active:
                            context['user_selected_tournament'] = selected
                        else:
                            # Fall back to first active
                            context['user_selected_tournament'] = active_tournaments[0] if active_tournaments else None
                    else:
                        context['user_selected_tournament'] = active_tournaments[0] if active_tournaments else None
                except Exception:
                    pass
            
            return context
        
        # Initial data sync
        try:
            from app.services.openligadb import OpenLigaDBClient
            client = OpenLigaDBClient()
            client.sync_matches()
        except Exception as e:
            print(f"Initial sync failed (expected if no data yet): {e}")
    
    return app
