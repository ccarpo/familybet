import os

class Config:
    # Core
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:////app/data/familybet.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # OpenLigaDB – fallback defaults if not set per-tournament in DB
    WORLD_CUP_LEAGUE_SHORTCUT = os.environ.get('WORLD_CUP_LEAGUE_SHORTCUT', 'wm26')
    WORLD_CUP_SEASON = int(os.environ.get('WORLD_CUP_SEASON', 2026))

    # API-Football (optional alternative data source)
    API_FOOTBALL_KEY = os.environ.get('API_FOOTBALL_KEY', '')

    # Email / SMTP (Flask-Mail) – on/off controlled via EmailSettings in DB
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'FamilyBet <noreply@familybet.app>')
