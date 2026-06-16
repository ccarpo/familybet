import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///familybet.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Magic link settings
    MAGIC_LINK_EXPIRY_HOURS = 24
    
    # OpenLigaDB settings
    OPENLIGADB_BASE_URL = 'https://api.openligadb.de'
    WORLD_CUP_LEAGUE_SHORTCUT = 'wm2026'
    WORLD_CUP_SEASON = 2026
    
    # Scheduler settings
    SYNC_INTERVAL_HOURS = 24
    
    # App settings
    BET_LOCK_MINUTES_BEFORE_MATCH = 0
