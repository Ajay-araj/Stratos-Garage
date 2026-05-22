from django.contrib import admin
from .models import (
    Category, BikeCompatibility, Product, ProductVariant,
    VariantAttribute, ProductImage, AttributeType, AttributeValue,
    Coupon, Review,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'slug', 'is_active', 'sort_order')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('sort_order', 'name')


@admin.register(BikeCompatibility)
class BikeCompatibilityAdmin(admin.ModelAdmin):
    list_display = ('brand', 'model', 'year_from', 'year_to', 'engine_cc')
    list_filter = ('brand',)
    search_fields = ('brand', 'model')


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ('image', 'alt_text', 'is_primary', 'sort_order', 'variant')


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ('sku', 'price', 'compare_price', 'is_active')
    show_change_link = True


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'seller', 'category', 'base_price', 'is_active', 'is_featured', 'created_at')
    list_filter = ('is_active', 'is_featured', 'category')
    search_fields = ('name', 'slug', 'brand', 'seller__store_name')
    prepopulated_fields = {'slug': ('name',)}
    raw_id_fields = ('seller', 'category')
    filter_horizontal = ('compatible_bikes',)
    inlines = [ProductVariantInline, ProductImageInline]
    readonly_fields = ('created_at', 'updated_at')


class VariantAttributeInline(admin.TabularInline):
    model = VariantAttribute
    extra = 0


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('sku', 'product', 'price', 'compare_price', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('sku', 'product__name')
    raw_id_fields = ('product',)
    inlines = [VariantAttributeInline]


@admin.register(AttributeType)
class AttributeTypeAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'name', 'slug', 'sort_order')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    list_display = ('attribute_type', 'value', 'display_value', 'sort_order')
    list_filter = ('attribute_type',)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'discount_value', 'is_active', 'times_used', 'valid_from', 'valid_until')
    list_filter = ('is_active', 'discount_type')
    search_fields = ('code',)
    readonly_fields = ('times_used',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'rating', 'is_verified_purchase', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'is_verified_purchase', 'rating')
    search_fields = ('user__username', 'product__name')
    raw_id_fields = ('user', 'product')
    actions = ['approve_reviews', 'reject_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
    approve_reviews.short_description = "Approve selected reviews"

    def reject_reviews(self, request, queryset):
        queryset.update(is_approved=False)
    reject_reviews.short_description = "Reject selected reviews"
