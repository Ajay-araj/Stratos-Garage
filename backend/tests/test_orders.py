"""
Cart, checkout, order lifecycle, shipment, and notification tests.
"""
import pytest
from decimal import Decimal
from rest_framework import status


# ─── Cart CRUD ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCart:
    add_url = '/api/orders/cart/add/'
    cart_url = '/api/orders/cart/'
    clear_url = '/api/orders/cart/clear/'

    def test_get_empty_cart(self, buyer_client):
        resp = buyer_client.get(self.cart_url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['item_count'] == 0
        assert resp.data['subtotal'] == '0.00'

    def test_add_to_cart_success(self, buyer_client, variant, inventory):
        resp = buyer_client.post(self.add_url, {
            'variant_id': variant.id, 'quantity': 2,
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['quantity'] == 2

    def test_add_same_variant_twice_accumulates(self, buyer_client, variant, inventory):
        """Adding the same variant twice must increase qty, not create two rows."""
        buyer_client.post(self.add_url, {'variant_id': variant.id, 'quantity': 2})
        resp = buyer_client.post(self.add_url, {'variant_id': variant.id, 'quantity': 3})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['quantity'] == 5

    def test_add_unauthenticated(self, api_client, variant):
        resp = api_client.post(self.add_url, {'variant_id': variant.id, 'quantity': 1})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_add_exceeds_stock(self, buyer_client, variant, inventory):
        resp = buyer_client.post(self.add_url, {
            'variant_id': variant.id, 'quantity': 999,
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_zero_quantity(self, buyer_client, variant, inventory):
        resp = buyer_client.post(self.add_url, {
            'variant_id': variant.id, 'quantity': 0,
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_negative_quantity(self, buyer_client, variant, inventory):
        resp = buyer_client.post(self.add_url, {
            'variant_id': variant.id, 'quantity': -1,
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_invalid_variant(self, buyer_client):
        resp = buyer_client.post(self.add_url, {'variant_id': 99999, 'quantity': 1})
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_add_missing_variant_id(self, buyer_client):
        resp = buyer_client.post(self.add_url, {'quantity': 1})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_inactive_variant_rejected(self, buyer_client, variant, inventory):
        variant.is_active = False
        variant.save(update_fields=['is_active'])
        resp = buyer_client.post(self.add_url, {'variant_id': variant.id, 'quantity': 1})
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_get_cart_with_items(self, buyer_client, cart_with_item):
        resp = buyer_client.get(self.cart_url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['item_count'] == 1
        assert Decimal(resp.data['subtotal']) > 0

    def test_reservation_created_on_add(self, buyer_client, variant, inventory):
        from inventory.models import StockReservation
        buyer_client.post(self.add_url, {'variant_id': variant.id, 'quantity': 3})
        assert StockReservation.objects.filter(
            variant=variant, is_released=False
        ).exists()

    def test_inventory_reserved_on_add(self, buyer_client, variant, inventory):
        from inventory.models import Inventory
        buyer_client.post(self.add_url, {'variant_id': variant.id, 'quantity': 3})
        inventory.refresh_from_db()
        assert inventory.quantity_reserved >= 3

    def test_clear_cart(self, buyer_client, cart_with_item):
        resp = buyer_client.delete(self.clear_url)
        assert resp.status_code == status.HTTP_200_OK
        get = buyer_client.get(self.cart_url)
        assert get.data['item_count'] == 0

    def test_clear_cart_releases_reservations(self, buyer_client, cart_with_item, inventory):
        from inventory.models import StockReservation
        buyer_client.delete(self.clear_url)
        active = StockReservation.objects.filter(
            variant=inventory.variant, is_released=False,
        )
        assert not active.exists()


# ─── Cart Item Update / Remove ────────────────────────────────────────────────

@pytest.mark.django_db
class TestCartItemUpdate:

    def _item_url(self, item_id):
        return f'/api/orders/cart/{item_id}/'

    def test_update_quantity_success(self, buyer_client, cart_with_item):
        item = cart_with_item.items.first()
        resp = buyer_client.patch(self._item_url(item.id), {'quantity': 4})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['quantity'] == 4

    def test_update_exceeds_stock(self, buyer_client, cart_with_item, inventory):
        item = cart_with_item.items.first()
        resp = buyer_client.patch(self._item_url(item.id), {'quantity': 9999})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_to_zero_rejected(self, buyer_client, cart_with_item):
        item = cart_with_item.items.first()
        resp = buyer_client.patch(self._item_url(item.id), {'quantity': 0})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_remove_item_success(self, buyer_client, cart_with_item):
        item = cart_with_item.items.first()
        resp = buyer_client.delete(self._item_url(item.id))
        assert resp.status_code == status.HTTP_200_OK

    def test_remove_item_releases_reservation(self, buyer_client, cart_with_item, inventory):
        from inventory.models import StockReservation
        item = cart_with_item.items.first()
        buyer_client.delete(self._item_url(item.id))
        active = StockReservation.objects.filter(cart_item=item, is_released=False)
        assert not active.exists()

    def test_cannot_modify_other_users_cart_item(self, buyer2_client, cart_with_item):
        """Buyer 2 cannot touch Buyer 1's cart item."""
        item = cart_with_item.items.first()
        resp = buyer2_client.patch(self._item_url(item.id), {'quantity': 9})
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ─── Coupon on Cart ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCartCoupon:
    url = '/api/orders/cart/coupon/'

    def test_apply_valid_coupon(self, buyer_client, cart_with_item, coupon):
        resp = buyer_client.post(self.url, {'code': 'SAVE10'})
        assert resp.status_code == status.HTTP_200_OK
        assert 'discount' in resp.data

    def test_remove_coupon_with_empty_code(self, buyer_client, cart_with_item, coupon):
        buyer_client.post(self.url, {'code': 'SAVE10'})
        resp = buyer_client.post(self.url, {'code': ''})
        assert resp.status_code == status.HTTP_200_OK

    def test_apply_expired_coupon_rejected(self, buyer_client, cart_with_item, expired_coupon):
        resp = buyer_client.post(self.url, {'code': 'EXPIRED'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_apply_nonexistent_coupon_rejected(self, buyer_client, cart_with_item):
        resp = buyer_client.post(self.url, {'code': 'FAKE99'})
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_cart_total_reflects_discount(self, buyer_client, cart_with_item, coupon):
        buyer_client.post(self.url, {'code': 'SAVE10'})
        resp = buyer_client.get('/api/orders/cart/')
        assert resp.status_code == status.HTTP_200_OK
        subtotal = Decimal(resp.data['subtotal'])
        total = Decimal(resp.data['total'])
        discount = Decimal(resp.data['discount_amount'])
        assert discount > 0
        assert total == subtotal - discount


# ─── Place Order ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPlaceOrder:
    url = '/api/orders/place/'

    def _shipping(self, **overrides):
        base = {
            'shipping_name': 'Test Buyer',
            'shipping_phone': '9876543210',
            'shipping_address_line1': '123 Test Street',
            'shipping_city': 'Mumbai',
            'shipping_state': 'Maharashtra',
            'shipping_pincode': '400001',
        }
        base.update(overrides)
        return base

    def test_place_order_success(self, buyer_client, cart_with_item):
        resp = buyer_client.post(self.url, self._shipping())
        assert resp.status_code == status.HTTP_201_CREATED
        assert 'order_number' in resp.data['order']
        assert resp.data['order']['order_status'] == 'pending'

    def test_place_order_empty_cart(self, buyer_client):
        """API returns 404 when no Cart exists yet, or 400 if cart is empty."""
        resp = buyer_client.post(self.url, self._shipping())
        assert resp.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND)

    def test_place_order_invalid_pincode(self, buyer_client, cart_with_item):
        resp = buyer_client.post(self.url, self._shipping(shipping_pincode='ABC'))
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_place_order_missing_required_fields(self, buyer_client, cart_with_item):
        resp = buyer_client.post(self.url, {'shipping_name': 'Only Name'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_place_order_unauthenticated(self, api_client, cart_with_item):
        resp = api_client.post(self.url, self._shipping())
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inventory_decremented_after_order(self, buyer_client, cart_with_item, inventory):
        initial = inventory.quantity_available
        buyer_client.post(self.url, self._shipping())
        inventory.refresh_from_db()
        assert inventory.quantity_available == initial - 2  # cart had 2 units

    def test_reservation_released_after_order(self, buyer_client, cart_with_item, inventory):
        from inventory.models import StockReservation
        buyer_client.post(self.url, self._shipping())
        active = StockReservation.objects.filter(
            cart_item__in=cart_with_item.items.all(), is_released=False,
        )
        assert not active.exists()

    def test_cart_cleared_after_order(self, buyer_client, cart_with_item):
        buyer_client.post(self.url, self._shipping())
        resp = buyer_client.get('/api/orders/cart/')
        assert resp.data['item_count'] == 0

    def test_order_creates_inventory_log(self, buyer_client, cart_with_item, variant):
        from inventory.models import InventoryLog
        buyer_client.post(self.url, self._shipping())
        log = InventoryLog.objects.filter(variant=variant, reason='purchase')
        assert log.exists()

    def test_coupon_usage_incremented_on_order(self, buyer_client, cart_with_item, coupon):
        buyer_client.post('/api/orders/cart/coupon/', {'code': 'SAVE10'})
        buyer_client.post(self.url, self._shipping())
        coupon.refresh_from_db()
        assert coupon.times_used == 1

    def test_seller_total_sales_incremented(self, buyer_client, cart_with_item, seller_profile):
        from sellers.models import Seller
        buyer_client.post(self.url, self._shipping())
        seller_profile.refresh_from_db()
        assert seller_profile.total_sales >= 2  # ordered 2 units


# ─── Order Management ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestOrderManagement:

    def test_list_orders(self, buyer_client, placed_order):
        resp = buyer_client.get('/api/orders/')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1

    def test_list_orders_unauthenticated(self, api_client):
        resp = api_client.get('/api/orders/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_order_detail(self, buyer_client, placed_order):
        resp = buyer_client.get(f'/api/orders/{placed_order.order_number}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['order_number'] == placed_order.order_number
        assert 'items' in resp.data
        assert 'item_count' in resp.data

    def test_cannot_access_other_users_order(self, buyer2_client, placed_order):
        resp = buyer2_client.get(f'/api/orders/{placed_order.order_number}/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_cancel_pending_order(self, buyer_client, placed_order):
        resp = buyer_client.post(f'/api/orders/{placed_order.order_number}/cancel/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['order']['order_status'] == 'cancelled'

    def test_cancel_confirmed_order(self, buyer_client, placed_order):
        placed_order.order_status = 'confirmed'
        placed_order.save()
        resp = buyer_client.post(f'/api/orders/{placed_order.order_number}/cancel/')
        assert resp.status_code == status.HTTP_200_OK

    def test_cancel_shipped_order_rejected(self, buyer_client, placed_order):
        placed_order.order_status = 'shipped'
        placed_order.save()
        resp = buyer_client.post(f'/api/orders/{placed_order.order_number}/cancel/')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_cancel_delivered_order_rejected(self, buyer_client, placed_order):
        placed_order.order_status = 'delivered'
        placed_order.save()
        resp = buyer_client.post(f'/api/orders/{placed_order.order_number}/cancel/')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_cancel_restores_inventory(self, buyer_client, placed_order, inventory):
        """After cancelling, quantity_available must increase by the ordered quantity."""
        # placed_order fixture deducted 2 units (set quantity_available=48).
        # Refresh to get the current DB value.
        inventory.refresh_from_db()
        qty_before = inventory.quantity_available
        buyer_client.post(f'/api/orders/{placed_order.order_number}/cancel/')
        inventory.refresh_from_db()
        order_qty = placed_order.items.first().quantity
        assert inventory.quantity_available == qty_before + order_qty

    def test_cancel_creates_inventory_log(self, buyer_client, placed_order, variant):
        from inventory.models import InventoryLog
        buyer_client.post(f'/api/orders/{placed_order.order_number}/cancel/')
        log = InventoryLog.objects.filter(variant=variant, reason='return')
        assert log.exists()

    def test_cancel_nonexistent_order(self, buyer_client):
        resp = buyer_client.post('/api/orders/SG-DOESNOTEXIST/cancel/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_return_request_on_delivered_order(self, buyer_client, placed_order):
        placed_order.order_status = 'delivered'
        placed_order.save()
        resp = buyer_client.post(
            f'/api/orders/{placed_order.order_number}/return/',
            {'reason': 'Item damaged on arrival'},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['order']['order_status'] == 'return_requested'

    def test_return_without_reason_rejected(self, buyer_client, placed_order):
        placed_order.order_status = 'delivered'
        placed_order.save()
        resp = buyer_client.post(
            f'/api/orders/{placed_order.order_number}/return/', {},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_return_on_non_delivered_rejected(self, buyer_client, placed_order):
        resp = buyer_client.post(
            f'/api/orders/{placed_order.order_number}/return/',
            {'reason': 'Changed my mind'},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_return_other_users_order(self, buyer2_client, placed_order):
        placed_order.order_status = 'delivered'
        placed_order.save()
        resp = buyer2_client.post(
            f'/api/orders/{placed_order.order_number}/return/',
            {'reason': 'Theft attempt'},
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ─── Shipment Updates ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestShipment:

    def _shipment_url(self, order_number):
        return f'/api/orders/{order_number}/shipment/'

    def test_seller_creates_shipment(self, seller_client, placed_order):
        resp = seller_client.patch(self._shipment_url(placed_order.order_number), {
            'tracking_number': 'TRACK123456',
            'carrier': 'delhivery',
            'status': 'booked',
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['tracking_number'] == 'TRACK123456'

    def test_shipment_in_transit_updates_order_status(self, seller_client, placed_order):
        placed_order.order_status = 'confirmed'
        placed_order.save()
        seller_client.patch(self._shipment_url(placed_order.order_number), {
            'tracking_number': 'TRACK789', 'carrier': 'bluedart', 'status': 'in_transit',
        })
        placed_order.refresh_from_db()
        assert placed_order.order_status == 'shipped'

    def test_shipment_delivered_updates_order_status(self, seller_client, placed_order):
        # Create shipment first
        seller_client.patch(self._shipment_url(placed_order.order_number), {
            'tracking_number': 'TRACK000', 'carrier': 'ekart', 'status': 'booked',
        })
        resp = seller_client.patch(self._shipment_url(placed_order.order_number), {
            'status': 'delivered',
        })
        assert resp.status_code == status.HTTP_200_OK
        placed_order.refresh_from_db()
        assert placed_order.order_status == 'delivered'

    def test_admin_can_update_shipment(self, admin_client, placed_order):
        resp = admin_client.patch(self._shipment_url(placed_order.order_number), {
            'tracking_number': 'ADMINTRACK', 'carrier': 'dtdc', 'status': 'booked',
        })
        assert resp.status_code == status.HTTP_200_OK

    def test_buyer_cannot_update_shipment(self, buyer_client, placed_order):
        resp = buyer_client.patch(self._shipment_url(placed_order.order_number), {
            'tracking_number': 'HACK', 'carrier': 'other', 'status': 'delivered',
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_rival_seller_cannot_update_shipment(self, seller2_client, placed_order):
        """Seller 2 has no items in placed_order (belongs to Seller 1)."""
        resp = seller2_client.patch(self._shipment_url(placed_order.order_number), {
            'tracking_number': 'ROGUE', 'carrier': 'fedex', 'status': 'delivered',
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# ─── Notifications ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestNotifications:
    url = '/api/orders/notifications/'

    def test_list_notifications(self, buyer_client, buyer):
        from orders.models import Notification
        Notification.objects.create(
            user=buyer,
            notification_type='general',
            title='Hello',
            message='Test notification',
        )
        resp = buyer_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) >= 1

    def test_notifications_require_auth(self, api_client):
        resp = api_client.get(self.url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_mark_notification_read(self, buyer_client, buyer):
        from orders.models import Notification
        notif = Notification.objects.create(
            user=buyer, notification_type='general',
            title='Hello', message='Body',
        )
        resp = buyer_client.post(f'{self.url}{notif.id}/read/')
        assert resp.status_code == status.HTTP_200_OK
        notif.refresh_from_db()
        assert notif.is_read is True

    def test_mark_all_read(self, buyer_client, buyer):
        from orders.models import Notification
        for i in range(3):
            Notification.objects.create(
                user=buyer, notification_type='general',
                title=f'Notif {i}', message='Body',
            )
        resp = buyer_client.post(f'{self.url}mark-all-read/')
        assert resp.status_code == status.HTTP_200_OK
        unread = buyer.notifications.filter(is_read=False).count()
        assert unread == 0

    def test_cannot_mark_other_users_notification(self, buyer2_client, buyer):
        from orders.models import Notification
        notif = Notification.objects.create(
            user=buyer, notification_type='general',
            title='Private', message='Body',
        )
        resp = buyer2_client.post(f'{self.url}{notif.id}/read/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND
