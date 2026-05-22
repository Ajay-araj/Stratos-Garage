"""
users/email_utils.py

Non-blocking email dispatcher.

Strategy:
  1. Try to queue via Celery (.delay()) with a fast Redis liveness check first.
  2. If Redis/Celery is unavailable, fall back to a Python daemon thread that
     sends the email directly via SMTP.

This guarantees the HTTP request ALWAYS returns immediately regardless of
whether Celery or Redis is running.
"""

import logging
import threading

logger = logging.getLogger(__name__)


def _is_celery_available() -> bool:
    """Cheap Redis ping — max 1 second wait."""
    try:
        import redis
        from django.conf import settings
        url = getattr(settings, 'REDIS_URL', 'redis://127.0.0.1:6379/0')
        r = redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
        r.ping()
        return True
    except Exception:
        return False


def _run_in_thread(fn, *args, **kwargs):
    """Spawn a daemon thread so it doesn't block shutdown."""
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t


# ─────────────────────────────────────────────────────────────
# Public helpers — call these from views instead of .delay()
# ─────────────────────────────────────────────────────────────

def dispatch_otp_email(user_email: str, otp_code: str):
    """Queue OTP email via Celery or thread-fallback. Never blocks."""
    from .tasks import send_otp_email_task

    if _is_celery_available():
        try:
            send_otp_email_task.delay(user_email, otp_code)
            logger.info(f"[email] OTP queued via Celery for {user_email}")
            return
        except Exception as e:
            logger.warning(f"[email] Celery queue failed, falling back to thread: {e}")

    # Fallback: send directly in background thread
    logger.info(f"[email] Sending OTP via thread for {user_email}")
    _run_in_thread(send_otp_email_task, user_email, otp_code)


def dispatch_welcome_email(user_email: str, first_name: str):
    from .tasks import send_welcome_email_task

    if _is_celery_available():
        try:
            send_welcome_email_task.delay(user_email, first_name)
            return
        except Exception as e:
            logger.warning(f"[email] Celery welcome email failed, using thread: {e}")

    _run_in_thread(send_welcome_email_task, user_email, first_name)


def dispatch_login_notification(user_email: str, ip: str, ua: str, ts: str, device: str = ''):
    from .tasks import send_login_notification_task

    if _is_celery_available():
        try:
            send_login_notification_task.delay(user_email, ip, ua, ts, device)
            return
        except Exception as e:
            logger.warning(f"[email] Celery login alert failed, using thread: {e}")

    _run_in_thread(send_login_notification_task, user_email, ip, ua, ts, device)


def dispatch_password_reset_email(user_email: str, name: str, reset_url: str):
    from .tasks import send_password_reset_email_task

    if _is_celery_available():
        try:
            send_password_reset_email_task.delay(user_email, name, reset_url)
            return
        except Exception as e:
            logger.warning(f"[email] Celery password reset failed, using thread: {e}")

    _run_in_thread(send_password_reset_email_task, user_email, name, reset_url)
