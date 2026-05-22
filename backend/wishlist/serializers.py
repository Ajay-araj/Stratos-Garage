from rest_framework import serializers
from .models import Wishlist, WishlistItem
from products.serializers import ProductListSerializer


class WishlistItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)

    class Meta:
        model = WishlistItem
        fields = ['id', 'product', 'added_at']
        read_only_fields = ['id', 'added_at']


class WishlistSerializer(serializers.ModelSerializer):
    items = WishlistItemSerializer(many=True, read_only=True)
    count = serializers.SerializerMethodField()

    class Meta:
        model = Wishlist
        fields = ['id', 'count', 'items', 'updated_at']
        read_only_fields = ['id', 'updated_at']

    def get_count(self, obj):
        return obj.items.count()
