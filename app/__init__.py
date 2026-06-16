from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    
    with app.app_context():
        # Import models to ensure they are registered
        from app.models import User, Match, Bet, TournamentBet, ScoringConfig
        
        # Create tables
        db.create_all()
        
        # Register blueprints
        from app.routes.auth import auth_bp
        from app.routes.main import main_bp
        from app.routes.bets import bets_bp
        from app.routes.admin import admin_bp
        from app.routes.api import api_bp
        
        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)
        app.register_blueprint(bets_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(api_bp, url_prefix='/api')
        
        # Initialize scheduler
        from app.services.scheduler import init_scheduler
        init_scheduler(app)
        
        # Initial data sync
        try:
            from app.services.openligadb import OpenLigaDBClient
            client = OpenLigaDBClient()
            client.sync_matches()
        except Exception as e:
            print(f"Initial sync failed (expected if no data yet): {e}")
    
    return app
