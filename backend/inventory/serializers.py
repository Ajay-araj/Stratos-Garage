from rest_framework import serializers
from .models import Inventory, InventoryLog, StockReservation


class InventorySerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source='variant.sku', read_only=True)
    quantity_sellable = serializers.IntegerField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Inventory
        fields = [
            'id', 'sku', 'quantity_available', 'quantity_reserved',
            'quantity_sellable', 'low_stock_threshold', 'is_low_stock',
            'last_updated',
        ]
        read_only_fields = ['id', 'sku', 'quantity_reserved', 'quantity_sellable', 'is_low_stock', 'last_updated']


class InventoryUpdateSerializer(serializers.Serializer):
    quantity_available = serializers.IntegerField(min_value=0, required=False)
    low_stock_threshold = serializers.IntegerField(min_value=0, required=False)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')


class InventoryLogSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source='variant.sku', read_only=True)
    performed_by = serializers.CharField(source='performed_by.username', read_only=True, default=None)
    reference_order = serializers.CharField(source='reference_order.order_number', read_only=True, default=None)

    class Meta:
        model = InventoryLog
        fields = [
            'id', 'sku', 'change_quantity', 'reason', 'notes',
            'reference_order', 'performed_by', 'created_at',
        ]
        read_only_fields = fields


class StockReservationSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(source='variant.sku', read_only=True)

    class Meta:
        model = StockReservation
        fields = [
            'id', 'sku', 'quantity_reserved', 'reserved_at', 'expires_at', 'is_released',
        ]
        read_only_fields = fields
