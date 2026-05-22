"""
Inventory tests: stock updates, reservations, low-stock alerts,
overselling prevention, bulk restock, and audit logs.
"""
import pytest
from decimal import Decimal
from rest_framework import status


# ─── Stock View & Update ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestVariantInventoryView:

    def test_get_inventory_own_variant(self, seller_client, variant, inventory):
        resp = seller_client.get(f'/api/inventory/{variant.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['quantity_available'] == 50
        assert resp.data['quantity_reserved'] == 0
        assert 'quantity_sellable' in resp.data
        assert 'is_low_stock' in resp.data

    def test_get_inventory_rival_variant_blocked(self, seller2_client, variant, inventory):
        """Seller 2 cannot read Seller 1's inventory."""
        resp = seller2_client.get(f'/api/inventory/{variant.id}/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_get_inventory_buyer_blocked(self, buyer_client, variant, inventory):
        resp = buyer_client.get(f'/api/inventory/{variant.id}/')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_set_inventory_quantity(self, seller_client, variant, inventory):
        resp = seller_client.patch(
            f'/api/inventory/{variant.id}/',
            {'quantity_available': 75},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['quantity_available'] == 75

    def test_set_inventory_threshold(self, seller_client, variant, inventory):
        resp = seller_client.patch(
            f'/api/inventory/{variant.id}/',
            {'low_stock_threshold': 10},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['low_stock_threshold'] == 10

    def test_inventory_update_creates_audit_log(self, seller_client, variant, inventory):
        from inventory.models import InventoryLog
        before = InventoryLog.objects.filter(variant=variant).count()
        seller_client.patch(
            f'/api/inventory/{variant.id}/',
            {'quantity_available': 80},
        )
        after = InventoryLog.objects.filter(variant=variant).count()
        assert after == before + 1

    def test_negative_quantity_rejected(self, seller_client, variant, inventory):
        resp = seller_client.patch(
            f'/api/inventory/{variant.id}/',
            {'quantity_available': -10},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_inventory_autocreated_on_first_access(self, seller_client, variant):
        """Inventory is auto-created with 0 stock if it doesn't exist yet."""
        from inventory.models import Inventory
        Inventory.objects.filter(variant=variant).delete()
        resp = seller_client.get(f'/api/inventory/{variant.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['quantity_available'] == 0

    def test_unverified_seller_blocked(self, unverified_seller_client, variant, inventory):
        resp = unverified_seller_client.patch(
            f'/api/inventory/{variant.id}/',
            {'quantity_available': 10},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ─── Audit Logs ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestInventoryLogs:

    def test_list_logs_own_variant(self, seller_client, variant, inventory):
        # Generate a log entry
        seller_client.patch(f'/api/inventory/{variant.id}/', {'quantity_available': 60})
        resp = seller_client.get(f'/api/inventory/{variant.id}/logs/')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1

    def test_log_has_expected_fields(self, seller_client, variant, inventory):
        seller_client.patch(f'/api/inventory/{variant.id}/', {'quantity_available': 60})
        resp = seller_client.get(f'/api/inventory/{variant.id}/logs/')
        entry = resp.data[0]
        for field in ('sku', 'change_quantity', 'reason', 'performed_by', 'created_at'):
            assert field in entry

    def test_list_logs_rival_variant_blocked(self, seller2_client, variant, inventory):
        resp = seller2_client.get(f'/api/inventory/{variant.id}/logs/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ─── Bulk Restock ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBulkRestock:
    url = '/api/inventory/restock/'

    def test_bulk_restock_single_variant(self, seller_client, variant, inventory):
        resp = seller_client.post(self.url, [
            {'variant_id': variant.id, 'quantity': 20, 'notes': 'Batch restock'},
        ], format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data['restocked']) == 1
        assert resp.data['restocked'][0]['new_quantity'] == 70  # 50 + 20

    def test_bulk_restock_multiple_variants(self, seller_client, variant, inventory):
        """Multiple entries in one call."""
        resp = seller_client.post(self.url, [
            {'variant_id': variant.id, 'quantity': 10},
            {'variant_id': variant.id, 'quantity': 5},
        ], format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data['restocked']) == 2

    def test_bulk_restock_partial_error(self, seller_client, variant, inventory):
        """Valid entries still succeed; invalid ones go to errors list."""
        resp = seller_client.post(self.url, [
            {'variant_id': variant.id, 'quantity': 5},
            {'variant_id': 99999, 'quantity': 5},  # doesn't exist
        ], format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data['restocked']) == 1
        assert len(resp.data['errors']) == 1

    def test_bulk_restock_zero_quantity_error(self, seller_client, variant, inventory):
        resp = seller_client.post(self.url, [
            {'variant_id': variant.id, 'quantity': 0},
        ], format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_restock_negative_quantity_error(self, seller_client, variant, inventory):
        resp = seller_client.post(self.url, [
            {'variant_id': variant.id, 'quantity': -5},
        ], format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_restock_rival_variant_blocked(self, seller_client, variant2, inventory2):
        """Seller 1 cannot restock Seller 2's variant.
        API may return 400 (all items rejected) or 200 with errors list."""
        resp = seller_client.post(self.url, [
            {'variant_id': variant2.id, 'quantity': 10},
        ], format='json')
        if resp.status_code == status.HTTP_200_OK:
            assert len(resp.data['restocked']) == 0
            assert len(resp.data['errors']) == 1
        else:
            assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_restock_empty_list_rejected(self, seller_client):
        resp = seller_client.post(self.url, [], format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_restock_buyer_blocked(self, buyer_client, variant, inventory):
        resp = buyer_client.post(self.url, [
            {'variant_id': variant.id, 'quantity': 10},
        ], format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_bulk_restock_creates_audit_logs(self, seller_client, variant, inventory):
        from inventory.models import InventoryLog
        count_before = InventoryLog.objects.filter(variant=variant).count()
        seller_client.post(self.url, [
            {'variant_id': variant.id, 'quantity': 15, 'notes': 'New shipment'},
        ], format='json')
        count_after = InventoryLog.objects.filter(variant=variant).count()
        assert count_after == count_before + 1


# ─── Low Stock Alerts ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestLowStockAlerts:
    url = '/api/inventory/low-stock/'

    def test_low_stock_detected(self, seller_client, variant, inventory):
        from inventory.models import Inventory
        Inventory.objects.filter(pk=inventory.pk).update(
            quantity_available=3, low_stock_threshold=5,
        )
        resp = seller_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['count'] >= 1
        skus = [r['sku'] for r in resp.data['results']]
        assert variant.sku in skus

    def test_sufficient_stock_not_in_alert(self, seller_client, variant, inventory):
        # inventory already has 50 units, threshold is 5 — should not appear
        resp = seller_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        skus = [r['sku'] for r in resp.data['results']]
        assert variant.sku not in skus

    def test_low_stock_response_fields(self, seller_client, variant, inventory):
        from inventory.models import Inventory
        Inventory.objects.filter(pk=inventory.pk).update(quantity_available=2)
        resp = seller_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        if resp.data['count'] > 0:
            entry = resp.data['results'][0]
            for field in ('variant_id', 'sku', 'quantity_available',
                          'quantity_reserved', 'quantity_sellable', 'low_stock_threshold'):
                assert field in entry

    def test_rival_seller_stock_not_visible(self, seller_client, variant2, inventory2):
        """Seller 1 cannot see Seller 2's low-stock alerts."""
        from inventory.models import Inventory
        Inventory.objects.filter(pk=inventory2.pk).update(quantity_available=1)
        resp = seller_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        skus = [r['sku'] for r in resp.data['results']]
        assert variant2.sku not in skus

    def test_buyer_cannot_access_low_stock(self, buyer_client):
        resp = buyer_client.get(self.url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ─── Overselling Prevention ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestOverselling:
    add_url = '/api/orders/cart/add/'

    def test_cannot_add_more_than_available(self, buyer_client, variant, inventory):
        """Cart add must refuse qty > sellable stock."""
        resp = buyer_client.post(self.add_url, {
            'variant_id': variant.id, 'quantity': 999,
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'available' in resp.data.get('error', '').lower() \
            or 'available' in str(resp.data).lower()

    def test_out_of_stock_variant_rejected(self, buyer_client, variant):
        from inventory.models import Inventory
        Inventory.objects.create(variant=variant, quantity_available=0)
        resp = buyer_client.post(self.add_url, {
            'variant_id': variant.id, 'quantity': 1,
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_reservations_reduce_effective_stock(self, buyer_client, buyer2_client,
                                                  variant, inventory):
        """After buyer adds 45 items, buyer2 can only add up to remaining 5."""
        from inventory.models import Inventory
        Inventory.objects.filter(pk=inventory.pk).update(quantity_available=50)
        buyer_client.post(self.add_url, {'variant_id': variant.id, 'quantity': 45})
        resp = buyer2_client.post(self.add_url, {'variant_id': variant.id, 'quantity': 10})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.slow
    def test_concurrent_add_does_not_oversell(self, transactional_db, django_user_model):
        """
        Simulates two concurrent add-to-cart calls competing for 5 units.
        Only one should succeed; combined reserved must never exceed stock.

        Uses `transactional_db` (not `db`) so data is actually committed and
        visible to worker threads — the default `db` fixture wraps everything
        in a savepoint, causing FK violations from other threads.
        """
        from decimal import Decimal as D
        from concurrent.futures import ThreadPoolExecutor
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken
        from sellers.models import Seller
        from products.models import Category, Product, ProductVariant
        from inventory.models import Inventory

        # ── Create test data with real commits ───────────────────────────────
        u1 = django_user_model.objects.create_user(
            username='conc_buyer1', email='conc1@test.com',
            password='TestPass123!', role='buyer',
        )
        u2 = django_user_model.objects.create_user(
            username='conc_buyer2', email='conc2@test.com',
            password='TestPass123!', role='buyer',
        )
        seller_u = django_user_model.objects.create_user(
            username='conc_seller', email='concseller@test.com',
            password='TestPass123!', role='seller',
        )
        seller = Seller.objects.create(
            user=seller_u, store_name='Concurrent Test Store',
            is_verified=True, verification_status='approved',
            commission_rate=D('10.00'),
        )
        cat = Category.objects.create(name='ConcTest', slug='conctest')
        prod = Product.objects.create(
            seller=seller, category=cat,
            name='Race Exhaust Conc', slug='race-exhaust-conc',
            base_price=D('999.00'), is_active=True,
        )
        variant = ProductVariant.objects.create(
            product=prod, sku='CONC-SKU-001',
            price=D('999.00'), is_active=True,
        )
        inv = Inventory.objects.create(
            variant=variant, quantity_available=5, quantity_reserved=0,
        )

        def add_to_cart(user):
            client = APIClient()
            token = RefreshToken.for_user(user)
            client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
            return client.post('/api/orders/cart/add/', {
                'variant_id': variant.id, 'quantity': 5,
            })

        with ThreadPoolExecutor(max_workers=2) as ex:
            f1 = ex.submit(add_to_cart, u1)
            f2 = ex.submit(add_to_cart, u2)
            r1, r2 = f1.result(), f2.result()

        # Both 200 is impossible (only 5 units, each wants 5)
        # At least one must fail
        statuses = {r1.status_code, r2.status_code}
        assert status.HTTP_400_BAD_REQUEST in statuses

        inv.refresh_from_db()
        assert inv.quantity_reserved <= inv.quantity_available
