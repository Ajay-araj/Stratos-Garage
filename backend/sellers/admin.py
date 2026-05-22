from django.contrib import admin
from .models import Seller


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ('store_name', 'user', 'is_verified', 'verification_status', 'rating', 'total_sales', 'created_at')
    list_filter = ('is_verified', 'verification_status')
    search_fields = ('store_name', 'user__username', 'gst_number', 'business_email')
    readonly_fields = ('rating', 'total_sales', 'created_at', 'updated_at')
    raw_id_fields = ('user',)
    actions = ['approve_sellers', 'reject_sellers']

    def approve_sellers(self, request, queryset):
        queryset.update(is_verified=True, verification_status='approved')
    approve_sellers.short_description = "Approve selected sellers"

    def reject_sellers(self, request, queryset):
        queryset.update(is_verified=False, verification_status='rejected')
    reject_sellers.short_description = "Reject selected sellers"
