from django.conf import settings
from django.db import models


class Payment(models.Model):
    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]
    PAYMENT_GATEWAYS = [
        ('razorpay', 'Razorpay'),
        ('phonepe', 'PhonePe'),
        ('cod', 'Cash on Delivery'),
    ]
    PAYMENT_METHODS = [
        ('upi', 'UPI'),
        ('card', 'Card'),
        ('netbanking', 'Net Banking'),
        ('cod', 'Cash on Delivery'),
        ('wallet', 'Wallet'),
    ]

    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.RESTRICT,
        related_name='payment'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name='payments'
    )
    payment_gateway = models.CharField(max_length=50, choices=PAYMENT_GATEWAYS)
    gateway_order_id = models.CharField(max_length=255, unique=True, blank=True)
    gateway_payment_id = models.CharField(max_length=255, null=True, blank=True)
    gateway_signature = models.CharField(max_length=512, null=True, blank=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='initiated', db_index=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, null=True, blank=True)
    failure_reason = models.TextField(blank=True, default='')

    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['gateway_order_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Payment #{self.id} [{self.status}] — {self.order.order_number}"


class Refund(models.Model):
    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    payment = models.ForeignKey(
        Payment,
        on_delete=models.RESTRICT,
        related_name='refunds'
    )
    order_item = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='refunds'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField(blank=True, default='')
    gateway_refund_id = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='initiated')
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Refund #{self.id} — {self.amount} INR [{self.status}]"


class SellerPayout(models.Model):
    PAYOUT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('failed', 'Failed'),
    ]

    payment = models.ForeignKey(
        Payment,
        on_delete=models.RESTRICT,
        related_name='seller_payouts'
    )
    seller = models.ForeignKey(
        'sellers.Seller',
        on_delete=models.RESTRICT,
        related_name='payouts'
    )
    order_item = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.RESTRICT,
        related_name='seller_payouts'
    )
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_commission = models.DecimalField(max_digits=10, decimal_places=2)
    seller_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payout_status = models.CharField(max_length=15, choices=PAYOUT_STATUS_CHOICES, default='pending', db_index=True)
    payout_reference = models.CharField(max_length=255, blank=True, default='')
    payout_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['seller', 'payout_status']),
        ]

    def __str__(self):
        return f"Payout #{self.id} — {self.seller.store_name} ({self.seller_amount} INR)"
