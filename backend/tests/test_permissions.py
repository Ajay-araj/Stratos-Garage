"""
Permission enforcement tests — verifies every critical access control rule
across all six domains: users, sellers, products, inventory, orders, payments.
"""
import pytest
from rest_framework import status


# ─── Unauthenticated Access ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestPublicVsProtected:
    """All public endpoints must return 200; all protected endpoints must return 401."""

    # Public endpoints
    def test_product_list_is_public(self, api_client, product):
        assert api_client.get('/api/products/').status_code == status.HTTP_200_OK

    def test_product_detail_is_public(self, api_client, product):
        assert api_client.get(f'/api/products/{product.slug}/').status_code == status.HTTP_200_OK

    def test_review_list_is_public(self, api_client, product):
        assert api_client.get(f'/api/products/{product.slug}/reviews/').status_code == status.HTTP_200_OK

    def test_seller_public_list_is_public(self, api_client):
        assert api_client.get('/api/sellers/').status_code == status.HTTP_200_OK

    def test_seller_public_detail_is_public(self, api_client, seller_profile):
        assert api_client.get(f'/api/sellers/{seller_profile.id}/').status_code == status.HTTP_200_OK

    def test_category_list_is_public(self, api_client, category):
        assert api_client.get('/api/products/categories/').status_code == status.HTTP_200_OK

    def test_bike_compat_list_is_public(self, api_client, bike_compat):
        assert api_client.get('/api/products/bikes/compatibility/').status_code == status.HTTP_200_OK

    def test_health_check_is_public(self, api_client):
        assert api_client.get('/api/health/').status_code == status.HTTP_200_OK

    # Protected endpoints — must return 401 without token
    def test_cart_requires_auth(self, api_client):
        assert api_client.get('/api/orders/cart/').status_code == status.HTTP_401_UNAUTHORIZED

    def test_order_list_requires_auth(self, api_client):
        assert api_client.get('/api/orders/').status_code == status.HTTP_401_UNAUTHORIZED

    def test_profile_requires_auth(self, api_client):
        assert api_client.get('/api/users/profile/').status_code == status.HTTP_401_UNAUTHORIZED

    def test_wishlist_requires_auth(self, api_client):
        assert api_client.get('/api/wishlist/').status_code == status.HTTP_401_UNAUTHORIZED

    def test_payment_detail_requires_auth(self, api_client):
        assert api_client.get('/api/payments/SG-FAKE/').status_code == status.HTTP_401_UNAUTHORIZED

    def test_notifications_require_auth(self, api_client):
        assert api_client.get('/api/orders/notifications/').status_code == status.HTTP_401_UNAUTHORIZED

    def test_seller_dashboard_requires_auth(self, api_client):
        assert api_client.get('/api/sellers/dashboard/').status_code == status.HTTP_401_UNAUTHORIZED


# ─── Verified Seller Gating ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestVerifiedSellerGating:
    """Unverified sellers must be 403 on all seller-only endpoints."""

    def test_unverified_cannot_access_dashboard(self, unverified_seller_client):
        resp = unverified_seller_client.get('/api/sellers/dashboard/')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_unverified_cannot_create_product(self, unverified_seller_client):
        resp = unverified_seller_client.post('/api/products/add/', {
            'name': 'Blocked', 'base_price': '100',
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_unverified_cannot_manage_inventory(self, unverified_seller_client, variant):
        resp = unverified_seller_client.patch(
            f'/api/inventory/{variant.id}/', {'quantity_available': 10},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_unverified_cannot_bulk_restock(self, unverified_seller_client, variant, inventory):
        resp = unverified_seller_client.post('/api/inventory/restock/', [
            {'variant_id': variant.id, 'quantity': 10},
        ], format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_unverified_cannot_view_low_stock(self, unverified_seller_client):
        resp = unverified_seller_client.get('/api/inventory/low-stock/')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_unverified_cannot_add_bike_compat(self, unverified_seller_client):
        resp = unverified_seller_client.post('/api/products/bikes/compatibility/add/', {
            'brand': 'Yamaha', 'model': 'R15', 'year_from': 2020,
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_verified_seller_can_access_dashboard(self, seller_client):
        resp = seller_client.get('/api/sellers/dashboard/')
        assert resp.status_code == status.HTTP_200_OK

    def test_verified_seller_can_create_product(self, seller_client):
        resp = seller_client.post('/api/products/add/', {
            'name': 'Legal Product', 'base_price': '999.00',
        })
        assert resp.status_code == status.HTTP_201_CREATED


# ─── Buyer Access Restrictions ────────────────────────────────────────────────

@pytest.mark.django_db
class TestBuyerAccess:
    """Buyers must be 403 on all seller/admin-only endpoints."""

    def test_buyer_cannot_access_seller_dashboard(self, buyer_client):
        resp = buyer_client.get('/api/sellers/dashboard/')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_buyer_cannot_create_product(self, buyer_client):
        resp = buyer_client.post('/api/products/add/', {
            'name': 'Fake', 'base_price': '100',
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_buyer_cannot_manage_product(self, buyer_client, product):
        resp = buyer_client.patch(
            f'/api/products/{product.slug}/manage/', {'name': 'Hijacked'},
        )
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    def test_buyer_cannot_update_inventory(self, buyer_client, variant, inventory):
        resp = buyer_client.patch(
            f'/api/inventory/{variant.id}/', {'quantity_available': 999},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_buyer_cannot_bulk_restock(self, buyer_client, variant, inventory):
        resp = buyer_client.post('/api/inventory/restock/', [
            {'variant_id': variant.id, 'quantity': 10},
        ], format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_buyer_cannot_view_low_stock(self, buyer_client):
        resp = buyer_client.get('/api/inventory/low-stock/')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_buyer_cannot_list_all_payouts(self, buyer_client):
        resp = buyer_client.get('/api/payments/payouts/')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_buyer_cannot_access_admin_seller_list(self, buyer_client):
        resp = buyer_client.get('/api/sellers/admin/')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_buyer_cannot_access_return_list(self, buyer_client):
        resp = buyer_client.get('/api/sellers/returns/')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_buyer_cannot_add_bike_compat(self, buyer_client):
        resp = buyer_client.post('/api/products/bikes/compatibility/add/', {
            'brand': 'Honda', 'model': 'CB300R', 'year_from': 2021,
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_buyer_cannot_create_coupon(self, buyer_client):
        from django.utils import timezone as tz
        from datetime import timedelta
        resp = buyer_client.post('/api/products/coupons/', {
            'code': 'BUYER100', 'discount_type': 'percentage',
            'discount_value': '100.00', 'is_active': True,
            'valid_from': (tz.now() - timedelta(days=1)).isoformat(),
            'valid_until': (tz.now() + timedelta(days=30)).isoformat(),
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_buyer_cannot_list_coupons(self, buyer_client, coupon):
        resp = buyer_client.get('/api/products/coupons/')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_buyer_can_validate_coupon(self, buyer_client, coupon):
        """Coupon validation is buyer-accessible; creation is admin-only."""
        resp = buyer_client.post('/api/products/coupons/validate/', {'code': 'SAVE10'})
        assert resp.status_code == status.HTTP_200_OK

    def test_buyer_cannot_update_shipment(self, buyer_client, placed_order):
        resp = buyer_client.patch(
            f'/api/orders/{placed_order.order_number}/shipment/',
            {'tracking_number': 'HACK', 'carrier': 'other', 'status': 'delivered'},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ─── Admin-Only Endpoints ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAdminEndpoints:

    def test_buyer_cannot_verify_seller(self, buyer_client, seller_profile):
        resp = buyer_client.post(
            f'/api/sellers/{seller_profile.id}/verify/', {'action': 'approve'},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_seller_cannot_verify_another_seller(self, seller_client, unverified_seller_profile):
        resp = seller_client.post(
            f'/api/sellers/{unverified_seller_profile.id}/verify/', {'action': 'approve'},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_verify_seller(self, admin_client, unverified_seller_profile):
        resp = admin_client.post(
            f'/api/sellers/{unverified_seller_profile.id}/verify/', {'action': 'approve'},
        )
        assert resp.status_code == status.HTTP_200_OK
        unverified_seller_profile.refresh_from_db()
        assert unverified_seller_profile.is_verified is True

    def test_admin_can_reject_seller(self, admin_client, unverified_seller_profile):
        resp = admin_client.post(
            f'/api/sellers/{unverified_seller_profile.id}/verify/', {'action': 'reject'},
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_admin_invalid_action_rejected(self, admin_client, unverified_seller_profile):
        resp = admin_client.post(
            f'/api/sellers/{unverified_seller_profile.id}/verify/', {'action': 'delete'},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_admin_can_approve_return(self, admin_client, placed_order):
        placed_order.order_status = 'return_requested'
        placed_order.save()
        resp = admin_client.post(
            f'/api/sellers/returns/{placed_order.order_number}/review/',
            {'action': 'approve'},
        )
        assert resp.status_code == status.HTTP_200_OK
        placed_order.refresh_from_db()
        assert placed_order.order_status == 'returned'

    def test_admin_can_reject_return(self, admin_client, placed_order):
        placed_order.order_status = 'return_requested'
        placed_order.save()
        resp = admin_client.post(
            f'/api/sellers/returns/{placed_order.order_number}/review/',
            {'action': 'reject'},
        )
        assert resp.status_code == status.HTTP_200_OK
        placed_order.refresh_from_db()
        assert placed_order.order_status == 'delivered'

    def test_seller_cannot_approve_returns(self, seller_client, placed_order):
        placed_order.order_status = 'return_requested'
        placed_order.save()
        resp = seller_client.post(
            f'/api/sellers/returns/{placed_order.order_number}/review/',
            {'action': 'approve'},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_return_approval_wrong_status(self, admin_client, placed_order):
        """Can only review orders in return_requested status."""
        resp = admin_client.post(
            f'/api/sellers/returns/{placed_order.order_number}/review/',
            {'action': 'approve'},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_admin_can_list_all_sellers(self, admin_client, seller_profile):
        resp = admin_client.get('/api/sellers/admin/')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1

    def test_admin_can_filter_sellers_by_status(self, admin_client, unverified_seller_profile):
        resp = admin_client.get('/api/sellers/admin/', {'status': 'pending'})
        assert resp.status_code == status.HTTP_200_OK
        assert all(s['verification_status'] == 'pending' for s in resp.data)


# ─── Cross-Seller Isolation ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestCrossSellerIsolation:
    """Seller 1 must never be able to touch Seller 2's resources."""

    def test_cannot_update_rival_product(self, seller_client, product2):
        resp = seller_client.patch(
            f'/api/products/{product2.slug}/manage/', {'name': 'Stolen'},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_delete_rival_product(self, seller_client, product2):
        resp = seller_client.delete(f'/api/products/{product2.slug}/manage/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_read_rival_inventory(self, seller_client, variant2, inventory2):
        resp = seller_client.get(f'/api/inventory/{variant2.id}/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_update_rival_inventory(self, seller_client, variant2, inventory2):
        resp = seller_client.patch(
            f'/api/inventory/{variant2.id}/', {'quantity_available': 0},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_update_rival_variant(self, seller_client, variant2):
        resp = seller_client.patch(
            f'/api/products/variants/{variant2.id}/', {'price': '1.00'},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND
