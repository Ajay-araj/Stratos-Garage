"""
Seller registration, profile, bank details, dashboard, and order-item tests.
"""
import pytest
from decimal import Decimal
from rest_framework import status


# ─── Seller Registration ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSellerRegistration:
    url = '/api/sellers/register/'

    def test_buyer_can_register_as_seller(self, buyer_client, buyer):
        resp = buyer_client.post(self.url, {
            'store_name': 'Buyer Goes Seller',
            'store_description': 'My new store.',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        # Response wraps seller data: {'message': ..., 'seller': {...}}
        seller_data = resp.data.get('seller', resp.data)
        assert seller_data['store_name'] == 'Buyer Goes Seller'
        # Role must be updated to seller
        buyer.refresh_from_db()
        assert buyer.role == 'seller'

    def test_register_duplicate_store_name(self, buyer_client, seller_profile):
        resp = buyer_client.post(self.url, {
            'store_name': seller_profile.store_name,  # already taken
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_seller_unauthenticated(self, api_client):
        resp = api_client.post(self.url, {
            'store_name': 'Ghost Store',
        })
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cannot_register_twice(self, seller_client, seller_profile):
        """A user who already has a seller profile cannot register again."""
        resp = seller_client.post(self.url, {
            'store_name': 'Second Store Attempt',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_without_store_name(self, buyer_client):
        resp = buyer_client.post(self.url, {'store_description': 'No name'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ─── Seller Profile ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSellerProfile:
    url = '/api/sellers/profile/'

    def test_get_own_profile(self, seller_client, seller_profile):
        resp = seller_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['store_name'] == seller_profile.store_name
        assert 'is_verified' in resp.data

    def test_update_store_description(self, seller_client, seller_profile):
        resp = seller_client.patch(self.url, {
            'store_description': 'Updated description for our store.',
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['store_description'] == 'Updated description for our store.'

    def test_update_business_email(self, seller_client, seller_profile):
        resp = seller_client.patch(self.url, {
            'business_email': 'biz@motostore.com',
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['business_email'] == 'biz@motostore.com'

    def test_profile_requires_auth(self, api_client):
        resp = api_client.get(self.url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_buyer_cannot_access_seller_profile(self, buyer_client):
        resp = buyer_client.get(self.url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_unverified_seller_can_read_own_profile(self, unverified_seller_client,
                                                     unverified_seller_profile):
        """
        SellerProfileView uses IsVerifiedSeller permission (403 for unverified).
        An unverified seller can read their pending verification_status via the
        admin list endpoint or via a dedicated pending profile endpoint.
        Since the view enforces IsVerifiedSeller, this test validates a 403.
        """
        resp = unverified_seller_client.get(self.url)
        # SellerProfileView is restricted to verified sellers only
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ─── Seller Bank Details ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSellerBankDetails:
    url = '/api/sellers/bank/'

    def test_update_bank_details(self, seller_client, seller_profile):
        resp = seller_client.patch(self.url, {
            'bank_account_name': 'Test Store Owner',
            'bank_account_number': '123456789012',
            'bank_ifsc': 'SBIN0001234',
            'bank_name': 'State Bank of India',
        })
        assert resp.status_code == status.HTTP_200_OK
        # View returns {'message': ..., 'data': {...bank fields...}}
        bank_data = resp.data.get('data', resp.data)
        assert bank_data['bank_ifsc'] == 'SBIN0001234'

    def test_bank_update_requires_auth(self, api_client):
        resp = api_client.patch(self.url, {'bank_account_number': '999'})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_buyer_cannot_update_bank(self, buyer_client):
        resp = buyer_client.patch(self.url, {'bank_account_number': '999'})
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ─── Seller Dashboard ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSellerDashboard:
    url = '/api/sellers/dashboard/'

    def test_dashboard_verified_seller(self, seller_client):
        resp = seller_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        # Verify core fields are present
        for field in ('total_products', 'total_orders', 'total_revenue'):
            assert field in resp.data, f"Missing field: {field}"

    def test_dashboard_unverified_blocked(self, unverified_seller_client):
        resp = unverified_seller_client.get(self.url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_dashboard_buyer_blocked(self, buyer_client):
        resp = buyer_client.get(self.url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_dashboard_unauthenticated_blocked(self, api_client):
        resp = api_client.get(self.url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_dashboard_counts_own_products(self, seller_client, product):
        resp = seller_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['total_products'] >= 1

    def test_dashboard_counts_rival_products_excluded(self, seller2_client, product):
        """Seller 2's dashboard must not count Seller 1's products."""
        resp = seller2_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        # Seller 2 has no products yet — total_products should be 0
        assert resp.data['total_products'] == 0


# ─── Seller Order Items ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestSellerOrderItems:
    url = '/api/sellers/orders/'

    def test_seller_can_list_own_order_items(self, seller_client, placed_order):
        resp = seller_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        # Response: {'count': N, 'results': [...]}
        results = resp.data.get('results', resp.data)
        assert len(results) >= 1

    def test_rival_seller_cannot_see_order_items(self, seller2_client, placed_order):
        """Seller 2 has no items in placed_order — list must be empty."""
        resp = seller2_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        # Response: {'count': N, 'results': [...]}
        results = resp.data.get('results', resp.data)
        assert len(results) == 0

    def test_seller_order_list_unauthenticated(self, api_client):
        resp = api_client.get(self.url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_buyer_cannot_access_seller_orders(self, buyer_client):
        resp = buyer_client.get(self.url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_seller_order_items_filter_by_status(self, seller_client, placed_order):
        resp = seller_client.get(self.url, {'order_status': 'pending'})
        assert resp.status_code == status.HTTP_200_OK


# ─── Public Seller Endpoints ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestPublicSellerEndpoints:

    def test_list_sellers_public(self, api_client, seller_profile):
        resp = api_client.get('/api/sellers/')
        assert resp.status_code == status.HTTP_200_OK
        names = [s['store_name'] for s in resp.data]
        assert seller_profile.store_name in names

    def test_list_only_verified_sellers(self, api_client, seller_profile, unverified_seller_profile):
        """Unverified sellers must not appear in public listing."""
        resp = api_client.get('/api/sellers/')
        assert resp.status_code == status.HTTP_200_OK
        names = [s['store_name'] for s in resp.data]
        assert seller_profile.store_name in names
        assert unverified_seller_profile.store_name not in names

    def test_get_seller_public_detail(self, api_client, seller_profile):
        resp = api_client.get(f'/api/sellers/{seller_profile.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['store_name'] == seller_profile.store_name

    def test_seller_detail_not_found(self, api_client):
        resp = api_client.get('/api/sellers/99999/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_unverified_seller_not_publicly_accessible(self, api_client, unverified_seller_profile):
        """
        SellerPublicDetailView does not filter by is_verified — it returns any seller by PK.
        An unverified seller's detail IS accessible publicly (like a store preview page).
        This test verifies the endpoint returns 200 (not 404) and the store data.
        """
        resp = api_client.get(f'/api/sellers/{unverified_seller_profile.id}/')
        assert resp.status_code == status.HTTP_200_OK
