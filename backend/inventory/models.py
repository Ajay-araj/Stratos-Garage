from django.conf import settings
from django.db import models


class Inventory(models.Model):
    variant = models.OneToOneField(
        'products.ProductVariant',
        on_delete=models.CASCADE,
        related_name='inventory'
    )
    quantity_available = models.PositiveIntegerField(default=0)
    quantity_reserved = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Inventories'

    def __str__(self):
        return f"Inventory — {self.variant.sku} ({self.quantity_available} available)"

    @property
    def quantity_sellable(self):
        return max(self.quantity_available - self.quantity_reserved, 0)

    @property
    def is_low_stock(self):
        return self.quantity_sellable <= self.low_stock_threshold


class InventoryLog(models.Model):
    REASON_CHOICES = [
        ('purchase', 'Purchase'),
        ('restock', 'Restock'),
        ('manual_adjustment', 'Manual Adjustment'),
        ('damage', 'Damage'),
        ('return', 'Return'),
        ('reservation', 'Reservation'),
        ('reservation_release', 'Reservation Release'),
    ]

    variant = models.ForeignKey(
        'products.ProductVariant',
        on_delete=models.RESTRICT,
        related_name='inventory_logs'
    )
    change_quantity = models.IntegerField()
    reason = models.CharField(max_length=25, choices=REASON_CHOICES)
    reference_order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_logs'
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_actions'
    )
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['variant', 'reason']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        sign = '+' if self.change_quantity >= 0 else ''
        return f"{self.variant.sku} {sign}{self.change_quantity} ({self.reason})"


class StockReservation(models.Model):
    variant = models.ForeignKey(
        'products.ProductVariant',
        on_delete=models.RESTRICT,
        related_name='stock_reservations'
    )
    cart_item = models.ForeignKey(
        'orders.CartItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_reservations'
    )
    order_item = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_reservations'
    )
    quantity_reserved = models.PositiveIntegerField()
    reserved_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_released = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['variant', 'is_released']),
            models.Index(fields=['expires_at', 'is_released']),
        ]

    def __str__(self):
        return f"Reserved {self.quantity_reserved} of {self.variant.sku}"