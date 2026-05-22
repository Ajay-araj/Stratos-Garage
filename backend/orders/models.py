from django.conf import settings
from django.db import models


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart'
    )
    coupon = models.ForeignKey(
        'products.Coupon',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='carts'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart — {self.user.username}"

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.select_related('variant').all())

    @property
    def discount_amount(self):
        if not self.coupon:
            return 0
        valid, _ = self.coupon.is_valid()
        if not valid:
            return 0
        sub = self.subtotal
        if sub < self.coupon.min_order_value:
            return 0
        if self.coupon.discount_type == 'percentage':
            discount = sub * self.coupon.discount_value / 100
            if self.coupon.max_discount_amount:
                discount = min(discount, self.coupon.max_discount_amount)
        else:
            discount = self.coupon.discount_value
        return round(discount, 2)

    @property
    def total(self):
        return max(self.subtotal - self.discount_amount, 0)


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(
        'products.ProductVariant',
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'variant')

    def __str__(self):
        return f"{self.variant} × {self.quantity}"

    @property
    def subtotal(self):
        return self.variant.price * self.quantity


class Order(models.Model):
    ORDER_STATUS = [
        ('pending', 'Pending'),
        ('payment_confirmed', 'Payment Confirmed'),
        ('packed', 'Packed'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out For Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('return_requested', 'Return Requested'),
        ('returned', 'Returned'),
    ]
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders'
    )
    order_number = models.CharField(max_length=30, unique=True, blank=True)

    coupon = models.ForeignKey(
        'products.Coupon',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    coupon_code = models.CharField(max_length=50, blank=True, default='')
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    order_status = models.CharField(max_length=25, choices=ORDER_STATUS, default='pending', db_index=True)
    payment_status = models.CharField(max_length=25, choices=PAYMENT_STATUS, default='pending', db_index=True)

    # Shipping snapshot
    shipping_name = models.CharField(max_length=255, blank=True, default='')
    shipping_phone = models.CharField(max_length=20, blank=True, default='')
    shipping_address_line1 = models.CharField(max_length=255, blank=True, default='')
    shipping_address_line2 = models.CharField(max_length=255, blank=True, default='')
    shipping_city = models.CharField(max_length=100, blank=True, default='')
    shipping_state = models.CharField(max_length=100, blank=True, default='')
    shipping_pincode = models.CharField(max_length=20, blank=True, default='')
    shipping_country = models.CharField(max_length=100, blank=True, default='India')

    expected_delivery = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'order_status']),
            models.Index(fields=['order_number']),
        ]

    def save(self, *args, **kwargs):
        if not self.order_number:
            import uuid
            self.order_number = f"SG-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.order_number} — {self.user.username}"


class OrderItem(models.Model):
    RETURN_STATUS = [
        ('none', 'None'),
        ('requested', 'Return Requested'),
        ('approved', 'Return Approved'),
        ('rejected', 'Return Rejected'),
        ('completed', 'Return Completed'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey(
        'products.ProductVariant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items'
    )
    seller = models.ForeignKey(
        'sellers.Seller',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items'
    )

    # Snapshot fields
    product_name = models.CharField(max_length=255)
    variant_sku = models.CharField(max_length=100, blank=True, default='')
    variant_description = models.CharField(max_length=500, blank=True, default='')
    product_image = models.URLField(blank=True, default='')

    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    return_status = models.CharField(max_length=15, choices=RETURN_STATUS, default='none')
    return_reason = models.TextField(blank=True, default='')

    class Meta:
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['seller']),
        ]

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class Shipment(models.Model):
    CARRIER_CHOICES = [
        ('delhivery', 'Delhivery'),
        ('bluedart', 'Blue Dart'),
        ('ekart', 'Ekart'),
        ('dtdc', 'DTDC'),
        ('fedex', 'FedEx'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('booked', 'Booked'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('returned', 'Returned'),
        ('failed_delivery', 'Failed Delivery'),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='shipment')
    carrier = models.CharField(max_length=20, choices=CARRIER_CHOICES, default='other')
    tracking_number = models.CharField(max_length=100, unique=True)
    tracking_url = models.URLField(blank=True, default='')
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='booked')
    estimated_delivery = models.DateField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['tracking_number']),
        ]

    def __str__(self):
        return f"Shipment for Order #{self.order.order_number} — {self.tracking_number}"


class Notification(models.Model):
    TYPE_CHOICES = [
        ('order_placed', 'Order Placed'),
        ('order_confirmed', 'Order Confirmed'),
        ('order_shipped', 'Order Shipped'),
        ('order_delivered', 'Order Delivered'),
        ('order_cancelled', 'Order Cancelled'),
        ('payment_success', 'Payment Successful'),
        ('payment_failed', 'Payment Failed'),
        ('review_reminder', 'Review Reminder'),
        ('general', 'General'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=25, choices=TYPE_CHOICES, default='general')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    related_order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"[{self.notification_type}] {self.title} → {self.user.username}"
