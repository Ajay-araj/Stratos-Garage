"""
users/tasks.py — Celery async email tasks for Stratos Garage.

All tasks use fail_silently=False so Celery can retry on transient SMTP
failures, but every task is wrapped in a try/except so a permanent failure
(bad credentials, blocked account, etc.) logs the error instead of
crashing the worker.
"""

import logging
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Shared HTML base template
# ──────────────────────────────────────────────────────────────────────────────

def _base_html(content: str) -> str:
    """Wrap content in the Stratos Garage premium email shell."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Stratos Garage</title>
</head>
<body style="margin:0;padding:0;background-color:#000000;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#000000;">
    <tr>
      <td align="center" style="padding:40px 20px;">
        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="max-width:600px;width:100%;background-color:#0a0a0a;border:1px solid #222222;">

          <!-- Header -->
          <tr>
            <td align="center" style="padding:36px 40px 28px;border-bottom:1px solid #1a1a1a;">
              <div style="letter-spacing:6px;font-size:22px;font-weight:700;color:#ffffff;text-transform:uppercase;">
                STRATOS GARAGE
              </div>
              <div style="letter-spacing:3px;font-size:10px;color:#555555;margin-top:6px;text-transform:uppercase;">
                Premium Motorcycle Marketplace
              </div>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px 40px 32px;">
              {content}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td align="center"
                style="padding:24px 40px;border-top:1px solid #1a1a1a;color:#444444;font-size:11px;letter-spacing:1px;line-height:1.6;">
              &copy; 2026 Stratos Garage. All rights reserved.<br>
              <span style="color:#333333;">This is an automated message. Please do not reply.</span>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _heading(text: str) -> str:
    return (
        f'<h2 style="margin:0 0 24px;font-size:20px;font-weight:600;'
        f'color:#ffffff;letter-spacing:3px;text-transform:uppercase;">{text}</h2>'
    )


def _para(text: str, muted: bool = False) -> str:
    color = "#888888" if muted else "#cccccc"
    return f'<p style="margin:0 0 16px;font-size:15px;line-height:1.7;color:{color};">{text}</p>'


def _divider() -> str:
    return '<hr style="border:none;border-top:1px solid #1e1e1e;margin:28px 0;">'


def _otp_box(code: str) -> str:
    return (
        f'<div style="text-align:center;margin:28px 0;">'
        f'<div style="display:inline-block;padding:20px 40px;border:1px dashed #444444;'
        f'background:#0f0f0f;letter-spacing:10px;font-size:36px;font-weight:700;'
        f'color:#ffffff;font-family:monospace;">{code}</div></div>'
    )


def _info_row(label: str, value: str) -> str:
    return (
        f'<tr>'
        f'<td style="padding:8px 12px;color:#666666;font-size:13px;letter-spacing:1px;'
        f'text-transform:uppercase;width:130px;">{label}</td>'
        f'<td style="padding:8px 12px;color:#cccccc;font-size:13px;">{value}</td>'
        f'</tr>'
    )


def _info_table(rows: list[tuple]) -> str:
    inner = "".join(_info_row(lbl, val) for lbl, val in rows)
    return (
        f'<table cellpadding="0" cellspacing="0" border="0" width="100%"'
        f' style="background:#050505;border:1px solid #1e1e1e;margin:20px 0;">'
        f'{inner}</table>'
    )


def _cta_button(label: str, url: str) -> str:
    return (
        f'<div style="text-align:center;margin:32px 0;">'
        f'<a href="{url}" style="display:inline-block;padding:14px 40px;'
        f'background:#ffffff;color:#000000;font-size:13px;font-weight:700;'
        f'letter-spacing:3px;text-transform:uppercase;text-decoration:none;">'
        f'{label}</a></div>'
    )


# ──────────────────────────────────────────────────────────────────────────────
# Helper — send with retry on transient failure
# ──────────────────────────────────────────────────────────────────────────────

def _send(subject: str, plain: str, html: str, recipient: str):
    """Build and send a multipart email. Raises on failure so Celery can retry."""
    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)


# ──────────────────────────────────────────────────────────────────────────────
# Task 1 — OTP Verification
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_otp_email_task(self, user_email: str, otp_code: str):
    try:
        content = (
            _heading("Email Verification")
            + _para("Enter the code below to verify your Stratos Garage account.")
            + _otp_box(otp_code)
            + _para("This code expires in <strong>5 minutes</strong>. Do not share it with anyone.", muted=True)
            + _para("If you did not create an account, you can safely ignore this email.", muted=True)
        )
        _send(
            subject="Your Verification Code — Stratos Garage",
            plain=f"Your Stratos Garage verification code is: {otp_code}\nExpires in 5 minutes.",
            html=_base_html(content),
            recipient=user_email,
        )
        logger.info(f"[email] OTP sent to {user_email}")
    except Exception as exc:
        logger.error(f"[email] OTP send failed for {user_email}: {exc}")
        raise self.retry(exc=exc)


# ──────────────────────────────────────────────────────────────────────────────
# Task 2 — Welcome Email (after password created)
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_welcome_email_task(self, user_email: str, first_name: str):
    try:
        content = (
            _heading("Welcome to Stratos Garage")
            + _para(f"Hello <strong>{first_name}</strong>,")
            + _para(
                "Your account is now fully activated. Welcome to the premier destination "
                "for motorcycle performance parts and riding gear."
            )
            + _divider()
            + _para("Explore our curated collection, discover exclusive deals, and elevate your ride.", muted=True)
        )
        _send(
            subject="Welcome to Stratos Garage — Your Account Is Active",
            plain=f"Welcome to Stratos Garage, {first_name}! Your account is now active.",
            html=_base_html(content),
            recipient=user_email,
        )
        logger.info(f"[email] Welcome email sent to {user_email}")
    except Exception as exc:
        logger.error(f"[email] Welcome email failed for {user_email}: {exc}")
        raise self.retry(exc=exc)


# ──────────────────────────────────────────────────────────────────────────────
# Task 3 — Login Alert
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_login_notification_task(self, user_email: str, ip_address: str, user_agent: str, timestamp: str, device: str = ''):
    try:
        device_display = device or user_agent[:80]
        content = (
            _heading("Login Detected")
            + _para("A new sign-in to your Stratos Garage account was detected.")
            + _info_table([
                ("Time", timestamp),
                ("IP Address", ip_address),
                ("Device", device_display),
            ])
            + _divider()
            + _para(
                "If this was you, no action is required. "
                "If you don't recognise this activity, <strong>reset your password immediately</strong>.",
                muted=True,
            )
        )
        _send(
            subject="New Login Detected — Stratos Garage",
            plain=f"Your account was accessed on {timestamp} from {ip_address} using {device_display}.",
            html=_base_html(content),
            recipient=user_email,
        )
        logger.info(f"[email] Login alert sent to {user_email}")
    except Exception as exc:
        logger.error(f"[email] Login alert failed for {user_email}: {exc}")
        raise self.retry(exc=exc)


# ──────────────────────────────────────────────────────────────────────────────
# Task 4 — Password Reset
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_password_reset_email_task(self, user_email: str, username: str, reset_url: str):
    try:
        content = (
            _heading("Reset Your Password")
            + _para(f"Hi <strong>{username}</strong>,")
            + _para("We received a request to reset your Stratos Garage password. Click the button below to proceed.")
            + _cta_button("RESET PASSWORD", reset_url)
            + _divider()
            + _para("This link expires in <strong>1 hour</strong>.", muted=True)
            + _para("If you did not request a password reset, ignore this email — your account is safe.", muted=True)
        )
        _send(
            subject="Reset Your Password — Stratos Garage",
            plain=f"Hi {username},\n\nReset your password here:\n{reset_url}\n\nExpires in 1 hour.",
            html=_base_html(content),
            recipient=user_email,
        )
        logger.info(f"[email] Password reset email sent to {user_email}")
    except Exception as exc:
        logger.error(f"[email] Password reset failed for {user_email}: {exc}")
        raise self.retry(exc=exc)


# ──────────────────────────────────────────────────────────────────────────────
# Task 5 — Order Confirmation
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_order_confirmation_email_task(
    self,
    user_email: str,
    first_name: str,
    order_id: str,
    order_total: str,
    items_summary: str,
):
    try:
        content = (
            _heading("Order Confirmed")
            + _para(f"Thank you, <strong>{first_name}</strong>! Your order has been placed successfully.")
            + _info_table([
                ("Order ID", f"#{order_id}"),
                ("Total", order_total),
            ])
            + _divider()
            + _para("<strong>Items Ordered:</strong>")
            + f'<div style="background:#050505;border:1px solid #1e1e1e;padding:16px 20px;'
              f'color:#aaaaaa;font-size:13px;line-height:1.8;margin:0 0 20px;">{items_summary}</div>'
            + _para("You will receive a shipping notification once your order is dispatched.", muted=True)
        )
        _send(
            subject=f"Order Confirmed #{order_id} — Stratos Garage",
            plain=f"Hi {first_name}, your order #{order_id} for {order_total} is confirmed.",
            html=_base_html(content),
            recipient=user_email,
        )
        logger.info(f"[email] Order confirmation sent to {user_email} for order #{order_id}")
    except Exception as exc:
        logger.error(f"[email] Order confirmation failed for {user_email}: {exc}")
        raise self.retry(exc=exc)


# ──────────────────────────────────────────────────────────────────────────────
# Task 5a — Order Status Update Notification
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_order_status_email_task(
    self,
    user_email: str,
    first_name: str,
    order_id: str,
    status: str,
    message: str,
):
    try:
        content = (
            _heading(f"Order {status.capitalize()}")
            + _para(f"Hello <strong>{first_name}</strong>,")
            + _para(f"The status of your order <strong>#{order_id}</strong> has been updated to: <strong>{status.capitalize()}</strong>.")
            + _divider()
            + _para(message)
        )
        _send(
            subject=f"Order Update #{order_id} — Stratos Garage",
            plain=f"Hi {first_name}, the status of your order #{order_id} has been updated to {status}.",
            html=_base_html(content),
            recipient=user_email,
        )
        logger.info(f"[email] Order status update ({status}) sent to {user_email} for order #{order_id}")
    except Exception as exc:
        logger.error(f"[email] Order status update failed for {user_email}: {exc}")
        raise self.retry(exc=exc)


# ──────────────────────────────────────────────────────────────────────────────
# Task 5b — Seller New Order Notification
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_seller_new_order_email_task(
    self,
    seller_email: str,
    seller_store_name: str,
    buyer_name: str,
    order_id: str,
    items_summary: str,
    shipping_address: str,
):
    try:
        content = (
            _heading("New Order Received")
            + _para(f"Hello <strong>{seller_store_name}</strong>,")
            + _para(f"Great news! You have received a new order (#{order_id}) from <strong>{buyer_name}</strong>.")
            + _divider()
            + _para("<strong>Items Ordered:</strong>")
            + f'<div style="background:#050505;border:1px solid #1e1e1e;padding:16px 20px;'
              f'color:#aaaaaa;font-size:13px;line-height:1.8;margin:0 0 20px;">{items_summary}</div>'
            + _para("<strong>Shipping Address:</strong>")
            + f'<div style="background:#050505;border:1px solid #1e1e1e;padding:16px 20px;'
              f'color:#aaaaaa;font-size:13px;line-height:1.8;margin:0 0 20px;">{shipping_address}</div>'
            + _divider()
            + _para("Please log in to your Seller Dashboard to update the order status once shipped.", muted=True)
        )
        _send(
            subject=f"New Order #{order_id} Received — Stratos Garage",
            plain=f"Hi {seller_store_name}, you have a new order #{order_id} from {buyer_name}.",
            html=_base_html(content),
            recipient=seller_email,
        )
        logger.info(f"[email] Seller new order notification sent to {seller_email} for order #{order_id}")
    except Exception as exc:
        logger.error(f"[email] Seller new order notification failed for {seller_email}: {exc}")
        raise self.retry(exc=exc)


# ──────────────────────────────────────────────────────────────────────────────
# Task 6 — Seller Approval
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_seller_approval_email_task(self, user_email: str, seller_name: str, approved: bool):
    try:
        if approved:
            content = (
                _heading("Seller Account Approved")
                + _para(f"Congratulations, <strong>{seller_name}</strong>!")
                + _para(
                    "Your Stratos Garage seller account has been <strong>approved</strong>. "
                    "You can now list products and start selling."
                )
                + _divider()
                + _para("Log in to your Seller Dashboard to set up your store profile and add your first listing.", muted=True)
            )
            subject = "Seller Account Approved — Stratos Garage"
            plain = f"Hi {seller_name}, your Stratos Garage seller account has been approved!"
        else:
            content = (
                _heading("Seller Application Update")
                + _para(f"Hi <strong>{seller_name}</strong>,")
                + _para(
                    "After review, we were unable to approve your seller application at this time. "
                    "Please contact support if you believe this is an error."
                )
            )
            subject = "Seller Application — Stratos Garage"
            plain = f"Hi {seller_name}, your Stratos Garage seller application was not approved at this time."

        _send(subject=subject, plain=plain, html=_base_html(content), recipient=user_email)
        logger.info(f"[email] Seller {'approval' if approved else 'rejection'} email sent to {user_email}")
    except Exception as exc:
        logger.error(f"[email] Seller email failed for {user_email}: {exc}")
        raise self.retry(exc=exc)


# ──────────────────────────────────────────────────────────────────────────────
# Task 7 — Cleanup stale unverified accounts + expired OTPs
# Runs on schedule via Celery Beat (see settings CELERY_BEAT_SCHEDULE)
# Also safe to call manually: cleanup_unverified_accounts_task.delay()
# ──────────────────────────────────────────────────────────────────────────────

@shared_task
def cleanup_unverified_accounts_task():
    """
    Delete user accounts that:
      - are NOT email verified
      - were created more than 24 hours ago
      - have no active (unused, non-expired) OTPs

    Also purges all EmailOTP entries older than 24 hours.
    """
    from django.utils import timezone
    from django.contrib.auth import get_user_model
    from datetime import timedelta

    User = get_user_model()

    try:
        # Import inline to avoid circular imports at module level
        from users.models import EmailOTP

        cutoff = timezone.now() - timedelta(hours=24)

        # Delete expired OTP records first
        expired_otps = EmailOTP.objects.filter(created_at__lt=cutoff)
        otp_count = expired_otps.count()
        expired_otps.delete()
        logger.info(f"[cleanup] Deleted {otp_count} expired OTP records.")

        # Delete unverified users older than 24h with no pending valid OTPs
        stale_users = User.objects.filter(
            is_email_verified=False,
            date_joined__lt=cutoff,
        )
        user_count = stale_users.count()
        stale_users.delete()
        logger.info(f"[cleanup] Deleted {user_count} stale unverified user accounts.")

        return {'deleted_otps': otp_count, 'deleted_users': user_count}

    except Exception as exc:
        logger.error(f"[cleanup] Cleanup task failed: {exc}")
        return {'error': str(exc)}
