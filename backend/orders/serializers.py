from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem, Shipment, Notification
from products.serializers import ProductVariantSerializer, ProductListSerializer


# ─── Cart ─────────────────────────────────────────────────────────────────────

class CartItemSerializer(serializers.ModelSerializer):
    variant = ProductVariantSerializer(read_only=True)
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    product_id = serializers.IntegerField(source='variant.product.id', read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'variant', 'product_name', 'product_id', 'thumbnail_url', 'quantity', 'subtotal', 'added_at']
        read_only_fields = ['id', 'added_at']

    def get_thumbnail_url(self, obj):
        request = self.context.get('request')
        images = list(obj.variant.product.images.all())
        primary = next((img for img in images if img.is_primary), None) or (images[0] if images else None)
        if primary:
            try:
                if request:
                    return request.build_absolute_uri(primary.image.url)
                return primary.image.url
            except Exception:
                return None
        return None


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    coupon_code = serializers.CharField(source='coupon.code', read_only=True, default=None)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'coupon_code', 'subtotal', 'discount_amount', 'total', 'item_count', 'updated_at']

    def get_item_count(self, obj):
        # Use prefetch cache — avoids redundant COUNT query
        return len(obj.items.all())


# ─── Shipping ─────────────────────────────────────────────────────────────────

class ShippingAddressSerializer(serializers.Serializer):
    shipping_name = serializers.CharField(max_length=255)
    shipping_phone = serializers.CharField(max_length=20)
    shipping_address_line1 = serializers.CharField(max_length=255)
    shipping_address_line2 = serializers.CharField(max_length=255, required=False, default='')
    shipping_city = serializers.CharField(max_length=100)
    shipping_state = serializers.CharField(max_length=100)
    shipping_pincode = serializers.CharField(max_length=20)
    shipping_country = serializers.CharField(max_length=100, default='India')
    notes = serializers.CharField(required=False, default='', allow_blank=True)

    def validate_shipping_pincode(self, value):
        if not value.isdigit() or len(value) != 6:
            raise serializers.ValidationError("Enter a valid 6-digit Indian pincode.")
        return value


# ─── Order Item ───────────────────────────────────────────────────────────────

class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_name', 'variant_sku', 'variant_description',
            'product_image', 'quantity', 'unit_price', 'subtotal',
            'return_status', 'return_reason',
        ]


# ─── Shipment ────────────────────────────────────────────────────────────────

class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = [
            'id', 'carrier', 'tracking_number', 'tracking_url',
            'status', 'estimated_delivery', 'shipped_at', 'delivered_at',
        ]
        read_only_fields = ['id']


# ─── Order ────────────────────────────────────────────────────────────────────

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipment = ShipmentSerializer(read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'order_status', 'payment_status',
            'subtotal', 'coupon_code', 'coupon_discount', 'total_price',
            'shipping_name', 'shipping_phone',
            'shipping_address_line1', 'shipping_address_line2',
            'shipping_city', 'shipping_state', 'shipping_pincode', 'shipping_country',
            'notes', 'items', 'shipment', 'item_count', 'expected_delivery',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'order_number', 'created_at', 'updated_at']

    def get_item_count(self, obj):
        # .count() bypasses the prefetch cache; len() uses it — zero extra queries
        return len(obj.items.all())


# ─── Notification ─────────────────────────────────────────────────────────────

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'message', 'is_read', 'related_order', 'created_at']
        read_only_fields = ['id', 'notification_type', 'title', 'message', 'related_order', 'created_at']
