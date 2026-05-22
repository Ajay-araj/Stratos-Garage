from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.db.models import Q, Avg, Count, Min, Exists, OuterRef, F

from sellers.models import Seller
from .models import (
    Category, Product, ProductVariant, ProductImage,
    AttributeType, BikeCompatibility, Coupon, Review,
)
from .serializers import (
    CategorySerializer, CategoryFlatSerializer,
    ProductListSerializer, ProductDetailSerializer, ProductWriteSerializer,
    ProductVariantSerializer, ProductVariantWriteSerializer,
    ProductImageSerializer, AttributeTypeSerializer,
    BikeCompatibilitySerializer, CouponSerializer, CouponValidateSerializer,
    ReviewSerializer,
)
from inventory.models import Inventory, InventoryLog
from Stratosgarage.permissions import IsVerifiedSeller, IsProductOwner, IsAdminUser, IsVerifiedSellerOrBuyer


# ─── Categories ───────────────────────────────────────────────────────────────

class CategoryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        roots = Category.objects.filter(parent=None, is_active=True).prefetch_related('children')
        return Response(CategorySerializer(roots, many=True).data)


class CategoryFlatListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cats = Category.objects.filter(is_active=True).order_by('name')
        return Response(CategoryFlatSerializer(cats, many=True).data)


# ─── Products ─────────────────────────────────────────────────────────────────

class ProductListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # Exists subquery: one DB join, not N per-row queries
        _in_stock_sq = Inventory.objects.filter(
            variant__product=OuterRef('pk'),
            quantity_available__gt=0,
        )
        # NOTE: annotation is named `has_stock` (not `in_stock`) to avoid
        # shadowing the Product.in_stock @property, which has no setter.
        # Django raises AttributeError when it tries setattr(obj, 'in_stock', value).
        qs = (
            Product.objects
            .filter(is_active=True)
            .select_related('seller', 'category')
            .prefetch_related('images', 'variants__inventory')
            .annotate(
                avg_rating=Avg('reviews__rating'),
                rev_count=Count('reviews', distinct=True),
                min_variant_price=Min('variants__price'),
                has_stock=Exists(_in_stock_sq),
            )
        )

        q = request.query_params.get('q', '') or request.query_params.get('search', '')
        q = q.strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(description__icontains=q) | Q(brand__icontains=q)
            )

        category = request.query_params.get('category')
        if category:
            qs = qs.filter(Q(category__slug=category) | Q(category__parent__slug=category))

        seller_id = request.query_params.get('seller')
        if seller_id:
            qs = qs.filter(seller_id=seller_id)

        brand = request.query_params.get('brand')
        if brand:
            qs = qs.filter(brand__icontains=brand)

        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        if min_price:
            qs = qs.filter(variants__price__gte=min_price)
        if max_price:
            qs = qs.filter(variants__price__lte=max_price)

        bike_brand = request.query_params.get('bike_brand')
        if bike_brand:
            qs = qs.filter(compatible_bikes__brand__icontains=bike_brand)

        bike_model = request.query_params.get('bike_model')
        if bike_model:
            qs = qs.filter(compatible_bikes__model__icontains=bike_model)

        featured = request.query_params.get('featured')
        if featured == 'true':
            qs = qs.filter(is_featured=True)

        in_stock = request.query_params.get('in_stock')
        if in_stock == 'true':
            qs = qs.filter(variants__inventory__quantity_available__gt=0)

        sort_map = {
            'price_asc': 'min_variant_price',
            'price_desc': '-min_variant_price',
            'rating': '-avg_rating',
            'newest': '-created_at',
            'name': 'name',
        }
        sort = request.query_params.get('sort', 'newest')
        qs = qs.order_by(sort_map.get(sort, '-created_at')).distinct()

        try:
            page_size = max(1, min(int(request.query_params.get('page_size', 12)), 100))
            page = max(1, int(request.query_params.get('page', 1)))
        except (ValueError, TypeError):
            page_size, page = 12, 1

        total = qs.count()
        start = (page - 1) * page_size
        serializer = ProductListSerializer(
            qs[start:start + page_size], many=True, context={'request': request}
        )

        return Response({
            "count": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
            "results": serializer.data,
        })


class ProductDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        product = get_object_or_404(
            Product.objects
            .select_related('seller', 'category')
            .prefetch_related(
                'images', 'compatible_bikes',
                'variants__attributes__attribute_type',
                'variants__inventory',
                'variants__images',
                'reviews__user',
            ),
            slug=slug, is_active=True
        )
        return Response(ProductDetailSerializer(product, context={'request': request}).data)


class ProductCreateView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedSellerOrBuyer]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request):
        seller, _ = Seller.objects.get_or_create(
            user=request.user,
            defaults={
                'store_name': f"{request.user.username}'s Garage",
                'is_verified': True,
                'verification_status': 'approved'
            }
        )
        
        # request.data might have 'price' but serializer expects 'base_price'
        data = request.data.dict() if hasattr(request.data, 'dict') else request.data.copy()
        if 'price' in data and 'base_price' not in data:
            data['base_price'] = data['price']

        serializer = ProductWriteSerializer(data=data)
        if serializer.is_valid():
            product = serializer.save(seller=seller)

            # Create default variant
            price = data.get('price', product.base_price)
            stock = data.get('stock', 1)
            sku = data.get('sku', f"SKU-{product.id}-{product.created_at.timestamp()}")
            
            variant = ProductVariant.objects.create(
                product=product,
                sku=sku,
                price=price
            )
            Inventory.objects.create(variant=variant, quantity_available=stock)

            # Upload Images if any
            images = request.FILES.getlist('images')
            for i, img in enumerate(images):
                ProductImage.objects.create(
                    product=product,
                    image=img,
                    alt_text=product.name,
                    is_primary=(i == 0)
                )

            return Response(
                ProductDetailSerializer(product, context={'request': request}).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductManageView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedSellerOrBuyer]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_product(self, request, slug):
        return get_object_or_404(Product, slug=slug, seller__user=request.user)

    def patch(self, request, slug):
        product = self.get_product(request, slug)
        serializer = ProductWriteSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Refresh to return authoritative DB state (slug may have been auto-generated)
            product.refresh_from_db()
            return Response(ProductDetailSerializer(product, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, slug):
        # Keep for backward compatibility if needed, but new endpoints are preferred
        product = self.get_product(request, slug)
        product.is_active = False
        product.save(update_fields=['is_active'])
        return Response({"message": "Product deactivated."}, status=status.HTTP_200_OK)


class ProductArchiveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        if request.user.is_staff or request.user.is_superuser:
            product = get_object_or_404(Product, slug=slug)
        else:
            product = get_object_or_404(Product, slug=slug, seller__user=request.user)
        
        product.is_active = False
        product.save(update_fields=['is_active'])
        return Response({"message": "Product archived."}, status=status.HTTP_200_OK)


class ProductDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, slug):
        if request.user.is_staff or request.user.is_superuser:
            product = get_object_or_404(Product, slug=slug)
        else:
            product = get_object_or_404(Product, slug=slug, seller__user=request.user)
        
        # Delete image files from storage
        for img in product.images.all():
            if img.image:
                img.image.delete(save=False)
                
        # Delete variants images if any (assuming variants might have images)
        for variant in product.variants.all():
            for v_img in variant.images.all():
                if v_img.image:
                    v_img.image.delete(save=False)
                    
        # Database records will be cascade deleted
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Variants ─────────────────────────────────────────────────────────────────

class VariantListCreateView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedSellerOrBuyer]

    def get(self, request, slug):
        product = get_object_or_404(Product, slug=slug, seller__user=request.user)
        variants = product.variants.prefetch_related('attributes__attribute_type', 'inventory', 'images')
        return Response(ProductVariantSerializer(variants, many=True).data)

    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug, seller__user=request.user)
        serializer = ProductVariantWriteSerializer(data=request.data)
        if serializer.is_valid():
            variant = serializer.save(product=product)
            initial_stock = 0
            try:
                initial_stock = int(request.data.get('initial_stock', 0))
            except (ValueError, TypeError):
                initial_stock = 0
            Inventory.objects.get_or_create(
                variant=variant,
                defaults={'quantity_available': initial_stock}
            )
            return Response(ProductVariantSerializer(variant).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VariantManageView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedSellerOrBuyer]

    def get_variant(self, request, variant_id):
        return get_object_or_404(ProductVariant, pk=variant_id, product__seller__user=request.user)

    def patch(self, request, variant_id):
        variant = self.get_variant(request, variant_id)
        serializer = ProductVariantWriteSerializer(variant, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Refresh to avoid returning stale in-memory state
            variant.refresh_from_db()
            return Response(ProductVariantSerializer(variant).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, variant_id):
        variant = self.get_variant(request, variant_id)
        variant.is_active = False
        variant.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Product Images ───────────────────────────────────────────────────────────

class ProductImageUploadView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedSellerOrBuyer]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug, seller__user=request.user)
        images = request.FILES.getlist('images')
        if not images:
            return Response({"error": "No images provided."}, status=status.HTTP_400_BAD_REQUEST)
        created = []
        for i, img in enumerate(images):
            is_primary = (i == 0) and not product.images.filter(is_primary=True).exists()
            obj = ProductImage.objects.create(
                product=product,
                image=img,
                alt_text=request.data.get('alt_text', product.name),
                is_primary=is_primary,
            )
            created.append(obj)
        return Response(
            ProductImageSerializer(created, many=True, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


# ─── Reviews ──────────────────────────────────────────────────────────────────

class ReviewListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        reviews = (
            product.reviews
            .filter(is_approved=True)
            .select_related('user')
            .order_by('-created_at')
        )
        return Response(ReviewSerializer(reviews, many=True, context={'request': request}).data)

    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug)
        if Review.objects.filter(user=request.user, product=product).exists():
            return Response(
                {"error": "You have already reviewed this product."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from orders.models import OrderItem
        is_verified = OrderItem.objects.filter(
            order__user=request.user,
            variant__product=product,
            order__order_status='delivered',
        ).exists()

        serializer = ReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, product=product, is_verified_purchase=is_verified)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReviewHelpfulView(APIView):
    """POST /api/products/<slug>/reviews/<pk>/helpful/ — Vote helpful."""
    permission_classes = [IsAuthenticated]

    def post(self, request, slug, pk):
        product = get_object_or_404(Product, slug=slug)
        review = get_object_or_404(Review, pk=pk, product=product, is_approved=True)
        if review.user == request.user:
            return Response({"error": "You cannot vote on your own review."}, status=status.HTTP_400_BAD_REQUEST)
        # Atomic increment — eliminates stale-read race condition
        Review.objects.filter(pk=review.pk).update(helpful_votes=F('helpful_votes') + 1)
        review.refresh_from_db(fields=['helpful_votes'])
        return Response({"helpful_votes": review.helpful_votes})


# ─── Attributes ───────────────────────────────────────────────────────────────

class AttributeTypeListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        attrs = AttributeType.objects.prefetch_related('values').all()
        return Response(AttributeTypeSerializer(attrs, many=True).data)


# ─── Bike Compatibility ───────────────────────────────────────────────────────

class BikeCompatibilityListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        brand = request.query_params.get('brand')
        qs = BikeCompatibility.objects.all()
        if brand:
            qs = qs.filter(brand__icontains=brand)
        return Response(BikeCompatibilitySerializer(qs, many=True).data)


class BikeCompatibilityCreateView(APIView):
    """POST /api/products/bikes/compatibility/ — Verified sellers or admins create bike entries."""
    permission_classes = [IsAuthenticated, IsVerifiedSellerOrBuyer]

    def post(self, request):
        serializer = BikeCompatibilitySerializer(data=request.data)
        if serializer.is_valid():
            obj, created = BikeCompatibility.objects.get_or_create(
                brand=serializer.validated_data['brand'],
                model=serializer.validated_data['model'],
                year_from=serializer.validated_data['year_from'],
                defaults={
                    'year_to': serializer.validated_data.get('year_to'),
                    'engine_cc': serializer.validated_data.get('engine_cc'),
                },
            )
            return Response(BikeCompatibilitySerializer(obj).data,
                            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductBikeCompatibilityView(APIView):
    """POST /DELETE /api/products/<slug>/bikes/ — Seller links/unlinks bikes."""
    permission_classes = [IsAuthenticated, IsVerifiedSellerOrBuyer]

    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug, seller__user=request.user)
        bike_ids = request.data.get('bike_ids', [])
        if not isinstance(bike_ids, list):
            return Response({"error": "bike_ids must be a list."}, status=status.HTTP_400_BAD_REQUEST)
        bikes = BikeCompatibility.objects.filter(pk__in=bike_ids)
        product.compatible_bikes.add(*bikes)
        return Response({"message": f"Linked {bikes.count()} bike(s)."})

    def delete(self, request, slug):
        product = get_object_or_404(Product, slug=slug, seller__user=request.user)
        bike_ids = request.data.get('bike_ids', [])
        bikes = BikeCompatibility.objects.filter(pk__in=bike_ids)
        product.compatible_bikes.remove(*bikes)
        return Response({"message": f"Unlinked {bikes.count()} bike(s)."})


# ─── Coupons ──────────────────────────────────────────────────────────────────

class CouponValidateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CouponValidateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        coupon = Coupon.objects.get(code=serializer.validated_data['code'].upper())
        return Response({
            "valid": True,
            "coupon": CouponSerializer(coupon).data,
        })


class CouponListCreateView(APIView):
    """Admin-only coupon management."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        coupons = Coupon.objects.all().order_by('-created_at')
        return Response(CouponSerializer(coupons, many=True).data)

    def post(self, request):
        serializer = CouponSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)