from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask import current_app
import atexit
from datetime import datetime, timedelta

scheduler = None
_app_ref = None


def init_scheduler(app):
    """Initialize the background scheduler for periodic tasks"""
    global scheduler, _app_ref

    # In Flask debug mode the reloader forks a child process — only start
    # the scheduler in the actual worker process, not the monitor process.
    import os
    if app.debug and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        return

    if scheduler is not None:
        return
    
    _app_ref = app
    scheduler = BackgroundScheduler()
    
    # Daily full sync (new matches, schedule updates)
    scheduler.add_job(
        func=sync_matches_job,
        trigger=IntervalTrigger(hours=24),
        id='sync_matches_daily',
        name='Daily sync from OpenLigaDB',
        replace_existing=True
    )
    
    # Smart sync every 15 minutes - only runs full sync when matches are live
    scheduler.add_job(
        func=smart_sync_job,
        trigger=IntervalTrigger(minutes=15),
        id='sync_matches_live',
        name='Live match sync (15min)',
        replace_existing=True
    )
    
    # Deadline reminders: check every hour for upcoming deadlines
    scheduler.add_job(
        func=deadline_reminder_job,
        trigger=IntervalTrigger(hours=1),
        id='deadline_reminders',
        name='Deadline reminder emails',
        replace_existing=True
    )
    
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    print("Scheduler initialized (daily + 15-min live sync + hourly deadline reminders)")


def _has_live_matches():
    """Check if any match is currently live or recently started but not finished.

    The 15-minute smart sync runs for up to 4 hours after a match start to
    catch delayed final results from the provider.
    """
    try:
        from app.models import Match
        now = datetime.utcnow()
        window_start = now - timedelta(hours=4)
        live = Match.query.filter(
            Match.is_finished == False,
            Match.match_date >= window_start,
            Match.match_date <= now
        ).first()
        return live is not None
    except Exception:
        return False


def smart_sync_job():
    """Sync only when matches are currently live."""
    global _app_ref
    if _app_ref is None:
        return
    with _app_ref.app_context():
        try:
            if not _has_live_matches():
                return  # No live matches - skip this tick
            
            from app.services.openligadb import OpenLigaDBClient
            from app.services.scoring import ScoringService
            from app.models import Tournament
            
            print(f"[Live Sync] Live matches detected - syncing at {datetime.utcnow().strftime('%H:%M')}")
            
            # Sync all active tournaments
            active_tournaments = Tournament.query.filter_by(is_active=True).all()
            for tournament in active_tournaments:
                if tournament.provider_type != 'manual':
                    try:
                        client = OpenLigaDBClient()
                        client.sync_matches()
                    except Exception as e:
                        print(f"[Live Sync] Failed for {tournament.name}: {e}")
            
            # Recalculate points for newly finished matches
            ScoringService.recalculate_all_match_points()

            # Send result notifications for finished matches not yet emailed
            from app.models import Match, EmailLog
            from app.services.email_service import send_match_result_notifications
            finished_matches = Match.query.filter(Match.is_finished == True).all()
            notify_matches = [
                m for m in finished_matches
                if not EmailLog.already_sent('match_result_queued', ref_id=str(m.id))
            ]
            if notify_matches:
                for match in notify_matches:
                    EmailLog.record('match_result_queued', ref_id=str(match.id))
                    send_match_result_notifications(match)
                print(f"[Live Sync] Notified for {len(notify_matches)} finished match(es)")
            
            print("[Live Sync] Done")
        except Exception as e:
            print(f"[Live Sync] Error: {e}")


def deadline_reminder_job():
    """Hourly job: send reminders 24h and 2h before round deadlines."""
    global _app_ref
    if _app_ref is None:
        return
    with _app_ref.app_context():
        try:
            from app.services.email_service import send_deadline_reminders
            sent_24 = send_deadline_reminders(hours_before=24)
            sent_2 = send_deadline_reminders(hours_before=2)
            if sent_24 + sent_2 > 0:
                print(f"[Reminders] {sent_24} (24h) + {sent_2} (2h) emails sent")
        except Exception as e:
            print(f"[Reminders] Error: {e}")


def sync_matches_job():
    """Daily job to sync matches from OpenLigaDB"""
    global _app_ref
    if _app_ref is None:
        return
    with _app_ref.app_context():
        try:
            from app.services.openligadb import OpenLigaDBClient
            client = OpenLigaDBClient()
            synced = client.sync_matches()
            print(f"[Daily Sync] Completed: {synced} matches synced")
        except Exception as e:
            print(f"[Daily Sync] Failed: {e}")


def trigger_manual_sync():
    """Manually trigger a sync (for admin use)"""
    global _app_ref
    if _app_ref is None:
        return 0
    with _app_ref.app_context():
        try:
            from app.services.openligadb import OpenLigaDBClient
            client = OpenLigaDBClient()
            return client.sync_matches()
        except Exception as e:
            print(f"Manual sync failed: {e}")
            return 0
