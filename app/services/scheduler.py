from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask import current_app
import atexit

scheduler = None

def init_scheduler(app):
    """Initialize the background scheduler for periodic tasks"""
    global scheduler
    
    if scheduler is not None:
        return
    
    scheduler = BackgroundScheduler()
    
    # Schedule match sync every 24 hours
    scheduler.add_job(
        func=sync_matches_job,
        trigger=IntervalTrigger(hours=24),
        id='sync_matches',
        name='Sync matches from OpenLigaDB',
        replace_existing=True
    )
    
    scheduler.start()
    
    # Shut down the scheduler when the app exits
    atexit.register(lambda: scheduler.shutdown())
    
    print("Scheduler initialized")

def sync_matches_job():
    """Job to sync matches from OpenLigaDB"""
    with current_app.app_context():
        try:
            from app.services.openligadb import OpenLigaDBClient
            client = OpenLigaDBClient()
            synced = client.sync_matches()
            print(f"Scheduled sync completed: {synced} new matches")
        except Exception as e:
            print(f"Scheduled sync failed: {e}")

def trigger_manual_sync():
    """Manually trigger a sync (for admin use)"""
    with current_app.app_context():
        try:
            from app.services.openligadb import OpenLigaDBClient
            client = OpenLigaDBClient()
            return client.sync_matches()
        except Exception as e:
            print(f"Manual sync failed: {e}")
            return 0
