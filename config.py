import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:////app/data/familybet.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Magic link settings
    MAGIC_LINK_EXPIRY_HOURS = 24
    
    # OpenLigaDB settings
    OPENLIGADB_BASE_URL = 'https://api.openligadb.de'
    WORLD_CUP_LEAGUE_SHORTCUT = 'wm2026'
    WORLD_CUP_SEASON = 2026
    
    # API-Football settings (alternative data source)
    API_FOOTBALL_KEY = os.environ.get('API_FOOTBALL_KEY') or '0a3cfd728bcef1bd81edc7998a0c5373'
    API_FOOTBALL_LEAGUE_ID = 1  # FIFA World Cup
    
    # Scheduler settings
    SYNC_INTERVAL_HOURS = 24
    
    # App settings
    BET_LOCK_MINUTES_BEFORE_MATCH = 0
    
    # Email / SMTP settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')        # e.g. familybet@gmail.com
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')        # App password
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'FamilyBet <noreply@familybet.app>')
    MAIL_ENABLED = os.environ.get('MAIL_ENABLED', 'false').lower() == 'true'  # Must be explicitly enabled
