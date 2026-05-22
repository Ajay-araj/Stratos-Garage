"""
Management command: release_expired_reservations
================================================
Release all StockReservation records whose `expires_at` is in the past and
which have not yet been released.  For each expired reservation the
`quantity_reserved` counter on the related Inventory row is decremented
atomically using an F() expression.

Run via cron (e.g. every 5 minutes) or Celery beat:
    python manage.py release_expired_reservations
"""

import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from inventory.models import Inventory, StockReservation

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Release expired stock reservations and sync quantity_reserved."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show how many reservations would be released without making changes.',
        )

    def handle(self, *args, **options):
        dry_run: bool = options['dry_run']
        now = timezone.now()

        expired_qs = StockReservation.objects.filter(
            is_released=False,
            expires_at__lte=now,
        ).select_related('variant')

        count = expired_qs.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No expired reservations to release."))
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] Would release {count} expired reservation(s)."
                )
            )
            return

        released = 0
        errors = 0

        # Process in batches of 500 to avoid huge single transactions
        BATCH_SIZE = 500
        offset = 0

        while True:
            batch_ids = list(
                expired_qs.values_list('id', flat=True)[offset:offset + BATCH_SIZE]
            )
            if not batch_ids:
                break

            try:
                with transaction.atomic():
                    # Fetch with lock to prevent concurrent modification
                    batch = StockReservation.objects.select_for_update().filter(
                        id__in=batch_ids,
                        is_released=False,  # double-check under lock
                    ).select_related('variant')

                    # Aggregate release quantities per variant
                    variant_release: dict[int, int] = {}
                    reservation_ids = []
                    for res in batch:
                        variant_id = res.variant_id
                        variant_release[variant_id] = (
                            variant_release.get(variant_id, 0) + res.quantity_reserved
                        )
                        reservation_ids.append(res.id)

                    # Bulk-mark as released
                    StockReservation.objects.filter(id__in=reservation_ids).update(
                        is_released=True
                    )

                    # Atomically decrement quantity_reserved per variant
                    for variant_id, qty in variant_release.items():
                        Inventory.objects.filter(variant_id=variant_id).update(
                            quantity_reserved=F('quantity_reserved') - qty
                        )

                    released += len(reservation_ids)

            except Exception as exc:
                errors += 1
                logger.error(
                    f"Error releasing reservation batch (offset={offset}): {exc}",
                    exc_info=True,
                )

            offset += BATCH_SIZE

        msg = f"Released {released} expired reservation(s)."
        if errors:
            msg += f"  {errors} batch(es) failed \u2014 check logs."
            self.stdout.write(self.style.ERROR(msg))
            logger.error(msg)
        else:
            self.stdout.write(self.style.SUCCESS(msg))
            logger.info(msg)
