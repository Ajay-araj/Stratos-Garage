from rest_framework import serializers
from .models import Seller


class SellerSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Seller
        fields = [
            'id', 'username', 'email', 'store_name', 'store_description',
            'store_logo', 'store_banner', 'business_email', 'business_phone',
            'gst_number', 'is_verified', 'verification_status',
            'rating', 'total_sales', 'commission_rate', 'created_at',
        ]
        read_only_fields = ['id', 'is_verified', 'verification_status', 'rating', 'total_sales', 'commission_rate', 'created_at']


class SellerPublicSerializer(serializers.ModelSerializer):
    """Minimal seller info — safe for product listing pages."""
    class Meta:
        model = Seller
        fields = ['id', 'store_name', 'store_logo', 'rating', 'total_sales', 'is_verified']


class SellerRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seller
        fields = ['store_name', 'store_description', 'business_email', 'business_phone', 'gst_number']

    def validate_store_name(self, value):
        if Seller.objects.filter(store_name=value).exists():
            raise serializers.ValidationError("This store name is already taken.")
        return value

    def create(self, validated_data):
        request = self.context['request']
        if request.user.role != 'seller':
            request.user.role = 'seller'
            request.user.save(update_fields=['role'])
        return Seller.objects.create(user=request.user, **validated_data)


class SellerBankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seller
        fields = ['bank_account_name', 'bank_account_number', 'bank_ifsc', 'bank_name']
