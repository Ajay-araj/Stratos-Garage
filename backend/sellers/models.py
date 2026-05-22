from django.conf import settings
from django.db import models
from django.core.validators import RegexValidator


class Seller(models.Model):
    VERIFICATION_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='seller_profile'
    )
    store_name = models.CharField(max_length=255, unique=True)
    store_description = models.TextField(blank=True, default='')
    store_logo = models.ImageField(upload_to='sellers/logos/', null=True, blank=True)
    store_banner = models.ImageField(upload_to='sellers/banners/', null=True, blank=True)

    # Contact
    business_email = models.EmailField(blank=True, default='')
    business_phone = models.CharField(max_length=15, blank=True, default='')
    business_address = models.TextField(blank=True, default='')

    # Tax / Legal
    gst_number = models.CharField(
        max_length=15,
        blank=True,
        default='',
        validators=[RegexValidator(
            r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$',
            'Enter a valid GST number.'
        )]
    )
    pan_number = models.CharField(max_length=10, blank=True, default='')

    # Bank details for payout
    bank_account_name = models.CharField(max_length=255, blank=True, default='')
    bank_account_number = models.CharField(max_length=20, blank=True, default='')
    bank_ifsc = models.CharField(max_length=11, blank=True, default='')
    bank_name = models.CharField(max_length=255, blank=True, default='')

    # Platform
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    is_verified = models.BooleanField(default=False)
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    products_sold = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['is_verified']),
            models.Index(fields=['verification_status']),
        ]

    def __str__(self):
        return self.store_name