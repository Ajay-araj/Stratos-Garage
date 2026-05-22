from rest_framework import serializers
from .models import (
    Category, BikeCompatibility, Product, ProductVariant,
    AttributeType, AttributeValue, VariantAttribute,
    ProductImage, Coupon, Review,
)
from sellers.serializers import SellerPublicSerializer


# ─── Attribute ────────────────────────────────────────────────────────────────

class AttributeTypeSerializer(serializers.ModelSerializer):
    values = serializers.SerializerMethodField()

    class Meta:
        model = AttributeType
        fields = ['id', 'name', 'slug', 'display_name', 'sort_order', 'values']

    def get_values(self, obj):
        # Hits prefetch cache — no extra query when view uses prefetch_related('values')
        return AttributeValueSerializer(obj.values.all(), many=True).data


class AttributeValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttributeValue
        fields = ['id', 'attribute_type', 'value', 'display_value', 'sort_order']


class VariantAttributeSerializer(serializers.ModelSerializer):
    attribute_type_name = serializers.CharField(source='attribute_type.display_name', read_only=True)

    class Meta:
        model = VariantAttribute
        fields = ['id', 'attribute_type', 'attribute_type_name', 'value']


# ─── Category ─────────────────────────────────────────────────────────────────

class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'parent', 'name', 'slug', 'description', 'image', 'is_active', 'sort_order', 'children']

    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return CategorySerializer(children, many=True).data


class CategoryFlatSerializer(serializers.ModelSerializer):
    """Flat list — for dropdown/filter usage."""
    full_name = serializers.CharField(source='__str__', read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'full_name', 'slug', 'parent']


# ─── Bike Compatibility ────────────────────────────────────────────────────────

class BikeCompatibilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = BikeCompatibility
        fields = ['id', 'brand', 'model', 'year_from', 'year_to', 'engine_cc']


# ─── Product Image ─────────────────────────────────────────────────────────────

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'sort_order', 'variant']


# ─── Product Variant ──────────────────────────────────────────────────────────

class ProductVariantSerializer(serializers.ModelSerializer):
    attributes = VariantAttributeSerializer(many=True, read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)
    discount_percent = serializers.FloatField(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            'id', 'sku', 'price', 'compare_price', 'weight_grams',
            'is_active', 'attributes', 'available_quantity', 'discount_percent',
            'images', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class ProductVariantWriteSerializer(serializers.ModelSerializer):
    """Used for create/update of variants by seller."""
    attributes = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )

    class Meta:
        model = ProductVariant
        fields = ['id', 'sku', 'price', 'compare_price', 'weight_grams', 'is_active', 'attributes']

    def validate_sku(self, value):
        qs = ProductVariant.objects.filter(sku=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("SKU already exists.")
        return value

    def create(self, validated_data):
        attributes_data = validated_data.pop('attributes', [])
        variant = ProductVariant.objects.create(**validated_data)
        for attr in attributes_data:
            attr_type = AttributeType.objects.get(id=attr['attribute_type'])
            VariantAttribute.objects.create(variant=variant, attribute_type=attr_type, value=attr['value'])
        return variant

    def update(self, instance, validated_data):
        attributes_data = validated_data.pop('attributes', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if attributes_data is not None:
            instance.attributes.all().delete()
            for attr in attributes_data:
                attr_type = AttributeType.objects.get(id=attr['attribute_type'])
                VariantAttribute.objects.create(variant=instance, attribute_type=attr_type, value=attr['value'])
        return instance


# ─── Review ───────────────────────────────────────────────────────────────────

class ReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    profile_picture = serializers.ImageField(source='user.profile_picture', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'username', 'profile_picture', 'rating', 'title',
            'comment', 'is_verified_purchase', 'helpful_votes', 'created_at',
        ]
        read_only_fields = ['id', 'username', 'profile_picture', 'is_verified_purchase', 'helpful_votes', 'created_at']


# ─── Product List (lightweight) ───────────────────────────────────────────────

class ProductListSerializer(serializers.ModelSerializer):
    seller = SellerPublicSerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, default='')
    primary_image = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()  # alias for frontend compat

    # Sources from the `has_stock` annotation injected by ProductListView.
    in_stock = serializers.BooleanField(source='has_stock', read_only=True, default=False)
    average_rating = serializers.FloatField(source='avg_rating', read_only=True, default=0)
    review_count = serializers.IntegerField(source='rev_count', read_only=True, default=0)
    min_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'seller', 'category_name', 'brand',
            'base_price', 'description', 'short_description',
            'primary_image', 'thumbnail_url', 'average_rating', 'review_count',
            'min_price', 'in_stock', 'is_featured', 'created_at',
        ]

    def get_primary_image(self, obj):
        request = self.context.get('request')
        images = obj.images.all()  # hits prefetch cache
        primary = next((img for img in images if img.is_primary), None) or next(iter(images), None)
        if primary and request:
            try:
                return request.build_absolute_uri(primary.image.url)
            except Exception:
                return None
        return None

    def get_thumbnail_url(self, obj):
        """Alias for get_primary_image — keeps frontend backward compat."""
        return self.get_primary_image(obj)

    def get_min_price(self, obj):
        annotated = getattr(obj, 'min_variant_price', None)
        if annotated is not None:
            return str(annotated)
        variants = obj.variants.filter(is_active=True)
        prices = [v.price for v in variants]
        return str(min(prices)) if prices else str(obj.base_price)


# ─── Product Detail (full) ────────────────────────────────────────────────────

class ProductDetailSerializer(serializers.ModelSerializer):
    seller = SellerPublicSerializer(read_only=True)
    category = CategoryFlatSerializer(read_only=True)
    compatible_bikes = BikeCompatibilitySerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)

    # FIX: use annotated values if present, fall back to model properties
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    in_stock = serializers.BooleanField(read_only=True)
    image = serializers.SerializerMethodField()
    price = serializers.DecimalField(source='base_price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'seller', 'category', 'brand',
            'description', 'short_description', 'base_price',
            'compatible_bikes', 'images', 'variants',
            'average_rating', 'review_count', 'in_stock',
            'is_featured', 'is_active', 'reviews',
            'meta_title', 'meta_description', 'created_at', 'updated_at',
            'image', 'price'
        ]

    def get_average_rating(self, obj):
        annotated = getattr(obj, 'avg_rating', None)
        if annotated is not None:
            return round(float(annotated), 1)
        return obj.average_rating

    def get_review_count(self, obj):
        annotated = getattr(obj, 'rev_count', None)
        if annotated is not None:
            return annotated
        return obj.review_count

    def get_image(self, obj):
        request = self.context.get('request')
        images = list(obj.images.all())
        primary = next((img for img in images if img.is_primary), None) or (images[0] if images else None)
        if primary:
            try:
                if request:
                    return request.build_absolute_uri(primary.image.url)
                return primary.image.url
            except Exception:
                return None
        return None


# ─── Product Write ─────────────────────────────────────────────────────────────

class ProductWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'brand', 'description', 'short_description',
            'base_price', 'sku_prefix', 'is_active', 'is_featured',
            'meta_title', 'meta_description',
        ]

    def validate_base_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0.")
        return value


# ─── Coupon ───────────────────────────────────────────────────────────────────

class CouponValidateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)

    def validate_code(self, value):
        try:
            coupon = Coupon.objects.get(code=value.upper(), is_active=True)
        except Coupon.DoesNotExist:
            raise serializers.ValidationError("Invalid coupon code.")
        valid, msg = coupon.is_valid()
        if not valid:
            raise serializers.ValidationError(msg)
        return value


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'description', 'discount_type', 'discount_value',
            'min_order_value', 'max_discount_amount', 'apply_to',
            'usage_limit', 'times_used', 'per_user_limit',
            'is_active', 'valid_from', 'valid_until',
        ]
        read_only_fields = ['id', 'times_used']