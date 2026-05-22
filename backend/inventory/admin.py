from django.contrib import admin
from .models import Inventory, InventoryLog, StockReservation


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ('variant', 'quantity_available', 'quantity_reserved', 'quantity_sellable', 'is_low_stock', 'last_updated')
    search_fields = ('variant__sku', 'variant__product__name')
    readonly_fields = ('last_updated', 'quantity_sellable', 'is_low_stock')

    def quantity_sellable(self, obj):
        return obj.quantity_sellable

    def is_low_stock(self, obj):
        return obj.is_low_stock
    is_low_stock.boolean = True


@admin.register(InventoryLog)
class InventoryLogAdmin(admin.ModelAdmin):
    list_display = ('variant', 'change_quantity', 'reason', 'performed_by', 'created_at')
    list_filter = ('reason',)
    search_fields = ('variant__sku',)
    readonly_fields = ('created_at',)
    raw_id_fields = ('variant', 'reference_order', 'performed_by')


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = ('variant', 'quantity_reserved', 'is_released', 'reserved_at', 'expires_at')
    list_filter = ('is_released',)
    raw_id_fields = ('variant', 'cart_item', 'order_item')
