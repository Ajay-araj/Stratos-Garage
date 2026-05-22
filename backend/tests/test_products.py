"""
Products, variants, reviews, bike compatibility, coupon, and inventory tests.
"""
import pytest
from decimal import Decimal
from rest_framework import status


# ─── Category ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCategories:

    def test_category_tree(self, api_client, category):
        resp = api_client.get('/api/products/categories/')
        assert resp.status_code == status.HTTP_200_OK
        assert any(c['slug'] == category.slug for c in resp.data)

    def test_category_flat(self, api_client, category, category2):
        resp = api_client.get('/api/products/categories/flat/')
        assert resp.status_code == status.HTTP_200_OK
        slugs = [c['slug'] for c in resp.data]
        assert category.slug in slugs
        assert category2.slug in slugs


# ─── Product List ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductList:
    url = '/api/products/'

    def test_list_products_public(self, api_client, product):
        resp = api_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        assert 'results' in resp.data
        assert resp.data['count'] >= 1

    def test_search_by_name(self, api_client, product):
        resp = api_client.get(self.url, {'q': 'Racing'})
        assert resp.status_code == status.HTTP_200_OK
        assert any(p['name'] == product.name for p in resp.data['results'])

    def test_search_no_match(self, api_client, product):
        resp = api_client.get(self.url, {'q': 'xxxxdoesnotexist'})
        assert resp.data['count'] == 0

    def test_filter_by_category(self, api_client, product):
        resp = api_client.get(self.url, {'category': product.category.slug})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['count'] >= 1

    def test_filter_by_brand(self, api_client, product):
        product.brand = 'Akrapovic'
        product.save(update_fields=['brand'])
        resp = api_client.get(self.url, {'brand': 'Akrapovic'})
        assert resp.data['count'] >= 1

    def test_filter_in_stock(self, api_client, product, inventory):
        resp = api_client.get(self.url, {'in_stock': 'true'})
        assert resp.status_code == status.HTTP_200_OK

    def test_filter_featured(self, api_client, product):
        product.is_featured = True
        product.save(update_fields=['is_featured'])
        resp = api_client.get(self.url, {'featured': 'true'})
        assert resp.data['count'] >= 1

    def test_sort_by_price_asc(self, api_client, product):
        resp = api_client.get(self.url, {'sort': 'price_asc'})
        assert resp.status_code == status.HTTP_200_OK

    def test_sort_by_newest(self, api_client, product):
        resp = api_client.get(self.url, {'sort': 'newest'})
        assert resp.status_code == status.HTTP_200_OK

    def test_pagination(self, api_client, product):
        resp = api_client.get(self.url, {'page': 1, 'page_size': 5})
        assert resp.status_code == status.HTTP_200_OK
        assert 'total_pages' in resp.data

    def test_inactive_product_not_listed(self, api_client, product):
        product.is_active = False
        product.save()
        resp = api_client.get(self.url)
        names = [p['name'] for p in resp.data['results']]
        assert product.name not in names


# ─── Product Detail ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductDetail:

    def test_get_product_detail(self, api_client, product, variant):
        resp = api_client.get(f'/api/products/{product.slug}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['slug'] == product.slug
        assert 'variants' in resp.data
        assert len(resp.data['variants']) == 1

    def test_product_not_found(self, api_client):
        resp = api_client.get('/api/products/does-not-exist/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_inactive_product_not_accessible(self, api_client, product):
        product.is_active = False
        product.save()
        resp = api_client.get(f'/api/products/{product.slug}/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ─── Product CRUD (Seller) ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductManagement:
    create_url = '/api/products/add/'

    def test_create_product_verified_seller(self, seller_client):
        resp = seller_client.post(self.create_url, {
            'name': 'New Slip-On Exhaust',
            'base_price': '1999.00',
            'description': 'Lightweight titanium slip-on.',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['name'] == 'New Slip-On Exhaust'
        # Slug must be auto-generated
        assert 'slug' in resp.data

    def test_create_product_unverified_seller(self, unverified_seller_client):
        resp = unverified_seller_client.post(self.create_url, {
            'name': 'Blocked Product', 'base_price': '999.00',
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_create_product_buyer_blocked(self, buyer_client):
        resp = buyer_client.post(self.create_url, {
            'name': 'Buyer Product', 'base_price': '999.00',
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_create_product_unauthenticated(self, api_client):
        resp = api_client.post(self.create_url, {
            'name': 'Ghost Product', 'base_price': '500.00',
        })
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_product_zero_price(self, seller_client):
        resp = seller_client.post(self.create_url, {
            'name': 'Zero Price', 'base_price': '0.00',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_own_product(self, seller_client, product):
        resp = seller_client.patch(
            f'/api/products/{product.slug}/manage/',
            {'name': 'Updated Exhaust Name'},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['name'] == 'Updated Exhaust Name'

    def test_deactivate_product(self, seller_client, product):
        resp = seller_client.delete(f'/api/products/{product.slug}/manage/')
        assert resp.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert product.is_active is False

    def test_cannot_update_rival_sellers_product(self, seller2_client, product):
        """Seller 2 cannot touch Seller 1's product."""
        resp = seller2_client.patch(
            f'/api/products/{product.slug}/manage/',
            {'name': 'Stolen'},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_buyer_cannot_update_product(self, buyer_client, product):
        resp = buyer_client.patch(
            f'/api/products/{product.slug}/manage/',
            {'name': 'Hijacked'},
        )
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)


# ─── Variants ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestVariants:

    def test_create_variant(self, seller_client, product):
        resp = seller_client.post(f'/api/products/{product.slug}/variants/', {
            'sku': 'EXH-SLIP-002',
            'price': '3999.00',
            'compare_price': '4500.00',
            'is_active': True,
            'initial_stock': 10,
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['sku'] == 'EXH-SLIP-002'

    def test_create_variant_duplicate_sku(self, seller_client, product, variant):
        resp = seller_client.post(f'/api/products/{product.slug}/variants/', {
            'sku': variant.sku,  # already taken
            'price': '1999.00',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_variant_price(self, seller_client, product, variant):
        resp = seller_client.patch(f'/api/products/variants/{variant.id}/', {
            'price': '3000.00',
        })
        assert resp.status_code == status.HTTP_200_OK
        assert Decimal(resp.data['price']) == Decimal('3000.00')

    def test_deactivate_variant(self, seller_client, variant):
        resp = seller_client.delete(f'/api/products/variants/{variant.id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        variant.refresh_from_db()
        assert variant.is_active is False

    def test_seller2_cannot_manage_seller1_variant(self, seller2_client, variant):
        resp = seller2_client.patch(f'/api/products/variants/{variant.id}/', {
            'price': '1.00',
        })
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_list_variants_own_product(self, seller_client, product, variant):
        resp = seller_client.get(f'/api/products/{product.slug}/variants/')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1


# ─── Bike Compatibility ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBikeCompatibility:

    def test_list_bike_compat_public(self, api_client, bike_compat):
        resp = api_client.get('/api/products/bikes/compatibility/')
        assert resp.status_code == status.HTTP_200_OK
        assert any(b['brand'] == 'Royal Enfield' for b in resp.data)

    def test_filter_by_brand(self, api_client, bike_compat):
        resp = api_client.get('/api/products/bikes/compatibility/', {'brand': 'Royal Enfield'})
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1

    def test_create_bike_compat_verified_seller(self, seller_client):
        resp = seller_client.post('/api/products/bikes/compatibility/add/', {
            'brand': 'KTM', 'model': 'Duke 390', 'year_from': 2019,
        })
        assert resp.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)

    def test_create_bike_compat_buyer_blocked(self, buyer_client):
        resp = buyer_client.post('/api/products/bikes/compatibility/add/', {
            'brand': 'Yamaha', 'model': 'R15', 'year_from': 2021,
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_link_bike_to_product(self, seller_client, product, bike_compat):
        resp = seller_client.post(
            f'/api/products/{product.slug}/bikes/',
            {'bike_ids': [bike_compat.id]},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert product.compatible_bikes.filter(pk=bike_compat.id).exists()

    def test_unlink_bike_from_product(self, seller_client, product, bike_compat):
        product.compatible_bikes.add(bike_compat)
        resp = seller_client.delete(
            f'/api/products/{product.slug}/bikes/',
            {'bike_ids': [bike_compat.id]},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        assert not product.compatible_bikes.filter(pk=bike_compat.id).exists()


# ─── Coupon ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCoupon:

    def test_validate_valid_coupon(self, buyer_client, coupon):
        resp = buyer_client.post('/api/products/coupons/validate/', {'code': 'SAVE10'})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['valid'] is True

    def test_validate_expired_coupon(self, buyer_client, expired_coupon):
        resp = buyer_client.post('/api/products/coupons/validate/', {'code': 'EXPIRED'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_validate_nonexistent_coupon(self, buyer_client):
        resp = buyer_client.post('/api/products/coupons/validate/', {'code': 'DOESNOTEXIST'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_validate_coupon_unauthenticated(self, api_client, coupon):
        resp = api_client.post('/api/products/coupons/validate/', {'code': 'SAVE10'})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_can_create_coupon(self, admin_client):
        from django.utils import timezone as tz
        from datetime import timedelta
        resp = admin_client.post('/api/products/coupons/', {
            'code': 'ADMIN20',
            'discount_type': 'fixed',
            'discount_value': '200.00',
            'min_order_value': '0.00',
            'is_active': True,
            'valid_from': (tz.now() - timedelta(days=1)).isoformat(),
            'valid_until': (tz.now() + timedelta(days=30)).isoformat(),
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED

    def test_buyer_cannot_create_coupon(self, buyer_client):
        from django.utils import timezone as tz
        from datetime import timedelta
        resp = buyer_client.post('/api/products/coupons/', {
            'code': 'HACK50',
            'discount_type': 'percentage',
            'discount_value': '50.00',
            'is_active': True,
            'valid_from': (tz.now() - timedelta(days=1)).isoformat(),
            'valid_until': (tz.now() + timedelta(days=30)).isoformat(),
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_seller_cannot_create_coupon(self, seller_client):
        from django.utils import timezone as tz
        from datetime import timedelta
        resp = seller_client.post('/api/products/coupons/', {
            'code': 'SELLERHACK',
            'discount_type': 'percentage',
            'discount_value': '25.00',
            'is_active': True,
            'valid_from': (tz.now() - timedelta(days=1)).isoformat(),
            'valid_until': (tz.now() + timedelta(days=30)).isoformat(),
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_list_coupons(self, admin_client, coupon):
        resp = admin_client.get('/api/products/coupons/')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1


# ─── Reviews ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestReviews:

    def test_list_reviews_public(self, api_client, product):
        resp = api_client.get(f'/api/products/{product.slug}/reviews/')
        assert resp.status_code == status.HTTP_200_OK

    def test_create_review_verified_purchase(self, buyer_client, product, delivered_order):
        resp = buyer_client.post(f'/api/products/{product.slug}/reviews/', {
            'rating': 5, 'title': 'Excellent!', 'comment': 'Great product.',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['is_verified_purchase'] is True

    def test_create_review_unverified_purchase(self, buyer_client, product):
        """Can review without a purchase — but not verified."""
        resp = buyer_client.post(f'/api/products/{product.slug}/reviews/', {
            'rating': 3, 'title': 'Okay', 'comment': 'Not bad.',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['is_verified_purchase'] is False

    def test_rating_out_of_range(self, buyer_client, product):
        resp = buyer_client.post(f'/api/products/{product.slug}/reviews/', {
            'rating': 10, 'title': 'Fake', 'comment': 'Too good.',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_rating_zero_invalid(self, buyer_client, product):
        resp = buyer_client.post(f'/api/products/{product.slug}/reviews/', {
            'rating': 0, 'title': 'Bad', 'comment': 'Very bad.',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_review_twice(self, buyer_client, product, delivered_order):
        buyer_client.post(f'/api/products/{product.slug}/reviews/', {
            'rating': 4, 'title': 'Good', 'comment': 'Nice.',
        })
        resp = buyer_client.post(f'/api/products/{product.slug}/reviews/', {
            'rating': 3, 'title': 'Second attempt', 'comment': 'Again.',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_review_requires_auth(self, api_client, product):
        resp = api_client.post(f'/api/products/{product.slug}/reviews/', {
            'rating': 5, 'title': 'Test', 'comment': 'Nice',
        })
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_helpful_vote(self, buyer_client, buyer2_client, product):
        # Buyer creates review
        review_resp = buyer_client.post(f'/api/products/{product.slug}/reviews/', {
            'rating': 4, 'title': 'Good', 'comment': 'Solid build.',
        })
        review_id = review_resp.data['id']
        # Buyer2 votes helpful
        resp = buyer2_client.post(
            f'/api/products/{product.slug}/reviews/{review_id}/helpful/',
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['helpful_votes'] == 1

    def test_cannot_vote_own_review(self, buyer_client, product):
        review_resp = buyer_client.post(f'/api/products/{product.slug}/reviews/', {
            'rating': 5, 'title': 'My Review', 'comment': 'Great!',
        })
        review_id = review_resp.data['id']
        resp = buyer_client.post(
            f'/api/products/{product.slug}/reviews/{review_id}/helpful/',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ─── Attribute Types ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAttributeTypes:

    def test_list_attribute_types(self, api_client, attribute_type):
        resp = api_client.get('/api/products/attributes/types/')
        assert resp.status_code == status.HTTP_200_OK
        names = [a['name'] for a in resp.data]
        assert attribute_type.name in names

    def test_attribute_type_has_values_field(self, api_client, attribute_type):
        resp = api_client.get('/api/products/attributes/types/')
        assert resp.status_code == status.HTTP_200_OK
        assert 'values' in resp.data[0]
