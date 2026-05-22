"""
Async Celery tasks for Stratos Garage.
"""
from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def release_expired_reservations_task(self):
    """Release expired stock reservations (runs every 5 min via Celery beat)."""
    from django.db import transaction
    from django.db.models import F
    from inventory.models import Inventory, StockReservation

    now = timezone.now()
    expired = StockReservation.objects.filter(is_released=False, expires_at__lte=now)
    count = expired.count()

    if count == 0:
        return {'released': 0}

    try:
        variant_release: dict[int, int] = {}
        ids = []
        for res in expired.select_related('variant'):
            variant_release[res.variant_id] = (
                variant_release.get(res.variant_id, 0) + res.quantity_reserved
            )
            ids.append(res.id)

        with transaction.atomic():
            StockReservation.objects.filter(id__in=ids).update(is_released=True)
            for variant_id, qty in variant_release.items():
                Inventory.objects.filter(variant_id=variant_id).update(
                    quantity_reserved=F('quantity_reserved') - qty
                )

        logger.info(f"[celery] Released {count} expired reservations.")
        return {'released': count}
    except Exception as exc:
        logger.error(f"[celery] release_expired_reservations_task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_order_confirmation_email_task(self, order_id: int):
    """Send order confirmation email asynchronously."""
    from django.core.mail import send_mail
    from django.conf import settings
    from orders.models import Order

    try:
        order = Order.objects.select_related('user').get(pk=order_id)
        send_mail(
            subject=f"Order #{order.order_number} Confirmed — Stratos Garage",
            message=(
                f"Hi {order.user.username},\n\n"
                f"Your order #{order.order_number} has been placed successfully.\n"
                f"Total: ₹{order.total_price}\n\n"
                f"Track your order at: {settings.FRONTEND_URL}/orders/{order.order_number}\n\n"
                f"Thank you for shopping with Stratos Garage!"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=False,
        )
        logger.info(f"[celery] Order confirmation email sent for order {order.order_number}")
        return {'sent': True, 'order': order.order_number}
    except Order.DoesNotExist:
        logger.warning(f"[celery] send_order_confirmation_email_task: order {order_id} not found")
        return {'sent': False}
    except Exception as exc:
        logger.error(f"[celery] Email task failed for order {order_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_password_reset_email_task(self, user_id: int, reset_url: str):
    """Send password reset email asynchronously."""
    from django.core.mail import send_mail
    from django.conf import settings
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
        send_mail(
            subject='Reset Your Stratos Garage Password',
            message=(
                f"Hi {user.username},\n\n"
                f"Click the link below to reset your password (expires in 1 hour):\n\n"
                f"{reset_url}\n\n"
                f"If you did not request this, please ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f"[celery] Password reset email sent to {user.email}")
        return {'sent': True}
    except Exception as exc:
        logger.error(f"[celery] Password reset email failed for user {user_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc)
