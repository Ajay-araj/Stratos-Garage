from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify


class Category(models.Model):
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children'
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True, default='')
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['parent', 'is_active']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} → {self.name}"
        return self.name

    @property
    def full_path(self):
        parts = [self.name]
        node = self.parent
        while node:
            parts.insert(0, node.name)
            node = node.parent
        return ' / '.join(parts)


class BikeCompatibility(models.Model):
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year_from = models.PositiveSmallIntegerField()
    year_to = models.PositiveSmallIntegerField(null=True, blank=True)
    engine_cc = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Bike Compatibilities'
        unique_together = ('brand', 'model', 'year_from')
        indexes = [
            models.Index(fields=['brand', 'model']),
        ]

    def __str__(self):
        yr = f"{self.year_from}–{self.year_to or 'present'}"
        return f"{self.brand} {self.model} ({yr})"


class Product(models.Model):
    seller = models.ForeignKey(
        'sellers.Seller',
        on_delete=models.CASCADE,
        related_name='products'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    compatible_bikes = models.ManyToManyField(
        BikeCompatibility,
        blank=True,
        related_name='products'
    )

    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True, default='')
    short_description = models.CharField(max_length=500, blank=True, default='')
    brand = models.CharField(max_length=100, blank=True, default='')
    sku_prefix = models.CharField(max_length=50, blank=True, default='')

    base_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    meta_title = models.CharField(max_length=255, blank=True, default='')
    meta_description = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['seller', 'is_active']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['is_featured']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def primary_image(self):
        img = self.images.filter(is_primary=True).first() or self.images.first()
        return img.image.url if img else None

    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if not reviews:
            return 0
        return round(sum(r.rating for r in reviews) / len(reviews), 1)

    @property
    def review_count(self):
        return self.reviews.count()

    @property
    def in_stock(self):
        return self.variants.filter(inventory__quantity_available__gt=0).exists()


class AttributeType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    display_name = models.CharField(max_length=100)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name


class AttributeValue(models.Model):
    attribute_type = models.ForeignKey(
        AttributeType,
        on_delete=models.CASCADE,
        related_name='values'
    )
    value = models.CharField(max_length=255)
    display_value = models.CharField(max_length=255, blank=True, default='')
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('attribute_type', 'value')
        ordering = ['sort_order', 'value']

    def __str__(self):
        return f"{self.attribute_type.display_name}: {self.value}"


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants'
    )
    sku = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    compare_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )
    weight_grams = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['product', 'is_active']),
        ]

    def __str__(self):
        attrs = ', '.join(
            f"{va.attribute_type.display_name}: {va.value}" for va in self.attributes.select_related('attribute_type')
        )
        return f"{self.product.name} [{attrs}] — SKU:{self.sku}"

    @property
    def discount_percent(self):
        if self.compare_price and self.compare_price > self.price:
            return round((1 - self.price / self.compare_price) * 100, 0)
        return 0

    @property
    def available_quantity(self):
        try:
            return self.inventory.quantity_available
        except Exception:
            return 0


class VariantAttribute(models.Model):
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='attributes'
    )
    attribute_type = models.ForeignKey(
        AttributeType,
        on_delete=models.PROTECT,
        related_name='variant_attributes'
    )
    value = models.CharField(max_length=255)

    class Meta:
        unique_together = ('variant', 'attribute_type')

    def __str__(self):
        return f"{self.attribute_type.display_name}: {self.value}"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='images'
    )
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=255, blank=True, default='')
    is_primary = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-is_primary', 'sort_order']

    def save(self, *args, **kwargs):
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for {self.product.name}"


class Coupon(models.Model):
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    APPLY_TO = [
        ('all', 'All Products'),
        ('category', 'Specific Category'),
        ('product', 'Specific Product'),
    ]

    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.CharField(max_length=255, blank=True, default='')
    discount_type = models.CharField(max_length=15, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    apply_to = models.CharField(max_length=10, choices=APPLY_TO, default='all')
    applicable_category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='coupons'
    )
    applicable_product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='coupons'
    )
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    times_used = models.PositiveIntegerField(default=0)
    per_user_limit = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['code', 'is_active']),
            models.Index(fields=['valid_from', 'valid_until']),
        ]

    def __str__(self):
        return f"Coupon {self.code} ({self.discount_type}: {self.discount_value})"

    def is_valid(self):
        from django.utils import timezone
        now = timezone.now()
        if not self.is_active:
            return False, "Coupon is not active."
        if now < self.valid_from:
            return False, "Coupon is not yet valid."
        if now > self.valid_until:
            return False, "Coupon has expired."
        if self.usage_limit and self.times_used >= self.usage_limit:
            return False, "Coupon usage limit reached."
        return True, "Valid"


class Review(models.Model):
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    order_item = models.OneToOneField(
        'orders.OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='review'
    )
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=255, blank=True, default='')
    comment = models.TextField(blank=True, default='')
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    helpful_votes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'product')
        indexes = [
            models.Index(fields=['product', 'is_approved']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user.username} → {self.product.name} ({self.rating}★)"