"""Email notification service for FamilyBet."""
from flask import current_app, render_template_string
from flask_mail import Message
from app import mail


def _get_settings():
    from app.models import EmailSettings
    try:
        return EmailSettings.get()
    except Exception:
        return None


def _mail_enabled():
    s = _get_settings()
    return s.enabled if s else False


def _apply_smtp_from_db():
    """Override Flask-Mail config with DB values if set."""
    s = _get_settings()
    if not s:
        return
    if s.mail_server:
        current_app.extensions['mail'].server = s.mail_server
        current_app.config['MAIL_SERVER'] = s.mail_server
    if s.mail_port:
        current_app.extensions['mail'].port = s.mail_port
        current_app.config['MAIL_PORT'] = s.mail_port
    if s.mail_username:
        current_app.extensions['mail'].username = s.mail_username
        current_app.config['MAIL_USERNAME'] = s.mail_username
    if s.mail_password:
        current_app.extensions['mail'].password = s.mail_password
        current_app.config['MAIL_PASSWORD'] = s.mail_password
    if s.mail_sender:
        current_app.extensions['mail'].default_sender = s.mail_sender
        current_app.config['MAIL_DEFAULT_SENDER'] = s.mail_sender
    current_app.extensions['mail'].use_tls = s.mail_use_tls
    current_app.config['MAIL_USE_TLS'] = s.mail_use_tls
    current_app.extensions['mail'].use_ssl = s.mail_use_ssl
    current_app.config['MAIL_USE_SSL'] = s.mail_use_ssl


def send_email(to, subject, html_body, text_body=None, force=False):
    """Send a single email. Returns True on success, False otherwise.
    
    force=True bypasses the enabled check (used for test emails).
    """
    if not force and not _mail_enabled():
        current_app.logger.info(f"[Email disabled] Would send '{subject}' to {to}")
        return False
    if not to:
        return False
    try:
        _apply_smtp_from_db()
        msg = Message(subject=subject, recipients=[to] if isinstance(to, str) else to)
        msg.html = html_body
        if text_body:
            msg.body = text_body
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Email send failed to {to}: {e}")
        raise


# ---------------------------------------------------------------------------
# Email templates (inline HTML)
# ---------------------------------------------------------------------------

_BASE = """
<!DOCTYPE html>
<html>
<body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#333">
<div style="background:#1d4ed8;padding:16px 20px;border-radius:8px 8px 0 0">
  <h2 style="color:white;margin:0">🏆 FamilyBet</h2>
</div>
<div style="background:#f9fafb;border:1px solid #e5e7eb;border-top:none;padding:20px;border-radius:0 0 8px 8px">
  {content}
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0">
  <p style="font-size:12px;color:#9ca3af">
    Du erhältst diese Email weil du bei FamilyBet registriert bist.<br>
    <a href="{unsubscribe_hint}" style="color:#6b7280">Benachrichtigungen deaktivieren</a>
  </p>
</div>
</body>
</html>
"""


def _render(content, user=None):
    hint = "Profil → Benachrichtigungen deaktivieren"
    return _BASE.format(content=content, unsubscribe_hint=hint)


# ---------------------------------------------------------------------------
# Notification functions
# ---------------------------------------------------------------------------

def notify_deadline_reminder(user, round_name, deadline, hours_left):
    """Remind user to place bets before round deadline."""
    s = _get_settings()
    email_type = 'deadline_24h' if hours_left >= 12 else 'deadline_2h'
    if not s or not s.is_enabled(email_type):
        return False
    if not user.email or not user.email_notifications:
        return False
    content = f"""
    <h3>⏰ Tipp-Deadline in {hours_left} Stunden</h3>
    <p>Hallo <strong>{user.name}</strong>,</p>
    <p>die Tipp-Deadline für die <strong>{round_name}</strong> läuft in 
    <strong>{hours_left} Stunden</strong> ab ({deadline.strftime('%d.%m.%Y um %H:%M Uhr')}).</p>
    <p>Vergiss nicht deine Tipps abzugeben!</p>
    <p style="margin-top:20px">
      <a href="#" style="background:#1d4ed8;color:white;padding:10px 20px;border-radius:6px;text-decoration:none">
        Jetzt tippen →
      </a>
    </p>
    """
    return send_email(user.email, f"⏰ Tipp-Deadline: {round_name} in {hours_left}h", _render(content))


def notify_match_result(user, match, bet):
    """Notify user of match result and their points."""
    s = _get_settings()
    if not s or not s.is_enabled('match_result'):
        return False
    if not user.email or not user.email_notifications:
        return False
    
    result = f"{match.team1_score}:{match.team2_score}"
    pred = f"{bet.team1_score_pred}:{bet.team2_score_pred}" if bet else "kein Tipp"
    points = bet.points_earned if bet else 0
    points_color = "#16a34a" if points > 0 else "#dc2626"
    
    content = f"""
    <h3>🏁 Spielergebnis: {match.team1_name} vs {match.team2_name}</h3>
    <p>Hallo <strong>{user.name}</strong>,</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0">
      <tr style="background:#f3f4f6">
        <td style="padding:8px 12px;font-weight:bold">Ergebnis</td>
        <td style="padding:8px 12px;font-size:1.4em;font-weight:bold;text-align:center">{result}</td>
      </tr>
      <tr>
        <td style="padding:8px 12px;font-weight:bold">Dein Tipp</td>
        <td style="padding:8px 12px;text-align:center">{pred}</td>
      </tr>
      <tr style="background:#f3f4f6">
        <td style="padding:8px 12px;font-weight:bold">Punkte</td>
        <td style="padding:8px 12px;text-align:center;font-weight:bold;color:{points_color};font-size:1.2em">{points} Punkte</td>
      </tr>
    </table>
    """
    subject = f"🏁 Ergebnis: {match.team1_name} {result} {match.team2_name} – {points} Punkte"
    return send_email(user.email, subject, _render(content))


def notify_leaderboard_change(user, new_rank, old_rank, total_points):
    """Notify user when their rank changes."""
    if not user.email or not user.email_notifications:
        return False
    
    if new_rank < old_rank:
        headline = f"🎉 Du bist jetzt auf Platz {new_rank}!"
        icon = "📈"
    else:
        headline = f"😬 Du bist auf Platz {new_rank} gefallen"
        icon = "📉"
    
    content = f"""
    <h3>{headline}</h3>
    <p>Hallo <strong>{user.name}</strong>,</p>
    <p>dein Rang hat sich geändert:</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0">
      <tr style="background:#f3f4f6">
        <td style="padding:8px 12px">Vorheriger Platz</td>
        <td style="padding:8px 12px;text-align:center;font-weight:bold">{icon} Platz {old_rank}</td>
      </tr>
      <tr>
        <td style="padding:8px 12px">Aktueller Platz</td>
        <td style="padding:8px 12px;text-align:center;font-weight:bold;font-size:1.3em">Platz {new_rank}</td>
      </tr>
      <tr style="background:#f3f4f6">
        <td style="padding:8px 12px">Gesamtpunkte</td>
        <td style="padding:8px 12px;text-align:center;font-weight:bold;color:#1d4ed8">{total_points} Punkte</td>
      </tr>
    </table>
    """
    return send_email(user.email, f"{headline} – FamilyBet Rangliste", _render(content))


def send_magic_link(user, magic_link_url):
    """Send magic login link via email."""
    s = _get_settings()
    if not s or not s.is_enabled('magic_link'):
        return False
    if not user.email:
        return False
    content = f"""
    <h3>🔐 Dein Login-Link für FamilyBet</h3>
    <p>Hallo <strong>{user.name}</strong>,</p>
    <p>du hast einen Login-Link angefordert. Klicke den Button um dich einzuloggen:</p>
    <p style="margin:24px 0;text-align:center">
      <a href="{magic_link_url}"
         style="background:#1d4ed8;color:white;padding:14px 28px;border-radius:8px;text-decoration:none;font-size:1.1em;font-weight:bold">
        Jetzt einloggen →
      </a>
    </p>
    <p style="color:#6b7280;font-size:0.9em">Dieser Link ist <strong>24 Stunden</strong> gültig und kann nur einmal verwendet werden.</p>
    <p style="color:#6b7280;font-size:0.9em">Falls du keinen Login angefordert hast, ignoriere diese Email einfach.</p>
    """
    return send_email(user.email, "🔐 FamilyBet – Dein Login-Link", _render(content))


def send_welcome_email(user):
    """Send welcome email when admin creates a new user account."""
    s = _get_settings()
    if not s or not s.is_enabled('welcome'):
        return False
    if not user.email:
        return False
    content = f"""
    <h3>👋 Willkommen bei FamilyBet!</h3>
    <p>Hallo <strong>{user.name}</strong>,</p>
    <p>du wurdest zu FamilyBet eingeladen! Melde dich mit deiner Email-Adresse an:</p>
    <p style="margin:24px 0;text-align:center">
      <a href="#"
         style="background:#1d4ed8;color:white;padding:14px 28px;border-radius:8px;text-decoration:none;font-size:1.1em;font-weight:bold">
        Jetzt anmelden →
      </a>
    </p>
    <p style="color:#6b7280;font-size:0.9em">Gib auf der Login-Seite deine Email-Adresse <strong>{user.email}</strong> ein um einen Login-Link zu erhalten.</p>
    """
    return send_email(user.email, "👋 Willkommen bei FamilyBet!", _render(content))


def send_test_email(to_email, user_name="Test"):
    """Send a test email to verify SMTP config. Always attempts regardless of enabled flag.
    
    Returns (True, None) on success or (False, error_message) on failure.
    """
    content = f"""
    <h3>✅ SMTP-Test erfolgreich!</h3>
    <p>Hallo <strong>{user_name}</strong>,</p>
    <p>diese Test-Email bestätigt dass FamilyBet Emails versenden kann.</p>
    <p style="color:#6b7280;font-size:0.9em">Gesendet von FamilyBet Admin</p>
    """
    try:
        send_email(to_email, "✅ FamilyBet – SMTP-Test", _render(content), force=True)
        return True, None
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# Batch notifications (called by scheduler)
# ---------------------------------------------------------------------------

def send_deadline_reminders(hours_before=24):
    """Send reminders for rounds whose deadline is in ~hours_before hours."""
    from datetime import datetime, timedelta
    from app.models import User, TournamentRound, Tournament, EmailLog

    now = datetime.utcnow()
    window_start = now + timedelta(hours=hours_before - 1)
    window_end = now + timedelta(hours=hours_before + 1)

    rounds = TournamentRound.query.filter(
        TournamentRound.deadline >= window_start,
        TournamentRound.deadline <= window_end
    ).all()

    if not rounds:
        return 0

    email_type = f'deadline_{hours_before}h'
    users = User.query.filter_by(email_notifications=True).filter(User.email.isnot(None)).all()
    sent = 0
    for t_round in rounds:
        ref_id = str(t_round.id)
        for user in users:
            if EmailLog.already_sent(email_type, user_id=user.id, ref_id=ref_id):
                continue
            ok = notify_deadline_reminder(user, t_round.name, t_round.deadline, hours_before)
            if ok:
                EmailLog.record(email_type, user_id=user.id, ref_id=ref_id)
                sent += 1

    current_app.logger.info(f"[Email] Sent {sent} deadline reminders ({hours_before}h window)")
    return sent


def send_match_result_notifications(match):
    """Send result notifications to all users who bet on a match."""
    from app.models import User, Bet, EmailLog

    email_type = 'match_result'
    ref_id = str(match.id)

    bets = Bet.query.filter_by(match_id=match.id).all()
    bet_by_user = {b.user_id: b for b in bets}

    users = User.query.filter_by(email_notifications=True).filter(User.email.isnot(None)).all()
    sent = 0
    for user in users:
        if EmailLog.already_sent(email_type, user_id=user.id, ref_id=ref_id):
            continue
        bet = bet_by_user.get(user.id)
        ok = notify_match_result(user, match, bet)
        if ok:
            EmailLog.record(email_type, user_id=user.id, ref_id=ref_id)
            sent += 1
    return sent
