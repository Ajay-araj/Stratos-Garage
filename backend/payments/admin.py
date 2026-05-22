from django.contrib import admin
from .models import Payment, Refund, SellerPayout


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'user', 'payment_gateway', 'amount', 'status', 'initiated_at')
    list_filter = ('payment_gateway', 'status')
    search_fields = ('gateway_order_id', 'gateway_payment_id', 'order__order_number')
    readonly_fields = ('initiated_at', 'completed_at')
    raw_id_fields = ('order', 'user')


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('id', 'payment', 'amount', 'status', 'initiated_at')
    list_filter = ('status',)
    readonly_fields = ('initiated_at', 'completed_at')


@admin.register(SellerPayout)
class SellerPayoutAdmin(admin.ModelAdmin):
    list_display = ('id', 'seller', 'gross_amount', 'platform_commission', 'seller_amount', 'payout_status', 'created_at')
    list_filter = ('payout_status',)
    search_fields = ('seller__store_name',)
    readonly_fields = ('created_at', 'gross_amount', 'platform_commission', 'seller_amount')
    raw_id_fields = ('payment', 'seller', 'order_item')
    actions = ['mark_completed']

    def mark_completed(self, request, queryset):
        from django.utils import timezone
        queryset.update(payout_status='completed', payout_date=timezone.now())
    mark_completed.short_description = "Mark selected payouts as completed"
