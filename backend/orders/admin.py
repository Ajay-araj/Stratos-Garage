from django.contrib import admin
from .models import Cart, CartItem, Order, OrderItem, Shipment, Notification


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    raw_id_fields = ('variant',)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'updated_at')
    raw_id_fields = ('user', 'coupon')
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'variant_sku', 'quantity', 'unit_price', 'subtotal')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'order_status', 'payment_status', 'total_price', 'created_at')
    list_filter = ('order_status', 'payment_status')
    search_fields = ('order_number', 'user__username', 'shipping_name', 'shipping_phone')
    readonly_fields = ('order_number', 'created_at', 'updated_at')
    raw_id_fields = ('user', 'coupon')
    inlines = [OrderItemInline]
    ordering = ('-created_at',)


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ('order', 'carrier', 'tracking_number', 'status', 'estimated_delivery')
    list_filter = ('carrier', 'status')
    search_fields = ('tracking_number', 'order__order_number')
    raw_id_fields = ('order',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('user__username', 'title')
    raw_id_fields = ('user', 'related_order')
