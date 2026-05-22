"""
Pure model unit tests — no HTTP, no views.
Tests: property logic, model validation, save() overrides, and constraint integrity.
"""
import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta


# ─── User Model ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.unit
class TestUserModel:

    def test_is_seller_property(self, seller_user):
        assert seller_user.is_seller is True
        assert seller_user.is_buyer is False

    def test_is_buyer_property(self, buyer):
        assert buyer.is_buyer is True
        assert buyer.is_seller is False

    def test_str_repr(self, buyer):
        assert 'buyer' in str(buyer)
        assert buyer.username in str(buyer)

    def test_email_unique_constraint(self, buyer, django_user_model):
        with pytest.raises(Exception):
            django_user_model.objects.create_user(
                username='dupe_email_user',
                email=buyer.email,     # duplicate
                password='Test123!',
            )

    def test_default_role_is_buyer(self, db, django_user_model):
        u = django_user_model.objects.create_user(
            username='noroleuser', email='norole@test.com', password='Test123!',
        )
        assert u.role == 'buyer'


# ─── Address Model ────────────────────────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.unit
class TestAddressModel:

    def _make_address(self, user, **kwargs):
        from users.models import Address
        defaults = dict(
            full_name='Test User', phone='9876543210',
            address_line1='123 Test St', city='Mumbai',
            state='Maharashtra', pincode='400001',
        )
        defaults.update(kwargs)
        return Address.objects.create(user=user, **defaults)

    def test_default_flag_only_one(self, buyer):
        a1 = self._make_address(buyer, is_default=True)
        a2 = self._make_address(buyer, is_default=True)
        a1.refresh_from_db()
        a2.refresh_from_db()
        assert a2.is_default is True
        assert a1.is_default is False   # auto-unset by save()

    def test_str_repr(self, buyer):
        addr = self._make_address(buyer)
        s = str(addr)
        assert 'Mumbai' in s


# ─── PasswordResetToken ───────────────────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.unit
class TestPasswordResetToken:

    def test_is_valid_fresh_token(self, buyer):
        from users.models import PasswordResetToken
        token = PasswordResetToken.objects.create(
            user=buyer, expires_at=timezone.now() + timedelta(hours=1),
        )
        assert token.is_valid is True

    def test_is_valid_expired_token(self, buyer):
        from users.models import PasswordResetToken
        token = PasswordResetToken.objects.create(
            user=buyer, expires_at=timezone.now() - timedelta(seconds=1),
        )
        assert token.is_valid is False

    def test_is_valid_used_token(self, buyer):
        from users.models import PasswordResetToken
        token = PasswordResetToken.objects.create(
            user=buyer,
            expires_at=timezone.now() + timedelta(hours=1),
            is_used=True,
        )
        assert token.is_valid is False

    def test_token_uuid_is_unique(self, buyer):
        from users.models import PasswordResetToken
        t1 = PasswordResetToken.objects.create(
            user=buyer, expires_at=timezone.now() + timedelta(hours=1),
        )
        t2 = PasswordResetToken.objects.create(
            user=buyer, expires_at=timezone.now() + timedelta(hours=1),
        )
        assert t1.token != t2.token


# ─── Product Model ────────────────────────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.unit
class TestProductModel:

    def test_slug_auto_generated(self, seller_profile, category):
        from products.models import Product
        p = Product.objects.create(
            seller=seller_profile, category=category,
            name='My Fancy Exhaust', base_price=Decimal('1999.00'),
        )
        assert p.slug == 'my-fancy-exhaust'

    def test_slug_deduplicated(self, seller_profile, category):
        from products.models import Product
        p1 = Product.objects.create(
            seller=seller_profile, category=category,
            name='Dup Product', base_price=Decimal('999.00'),
        )
        p2 = Product.objects.create(
            seller=seller_profile, category=category,
            name='Dup Product', base_price=Decimal('999.00'),
        )
        assert p1.slug != p2.slug
        assert p2.slug.startswith('dup-product-')

    def test_average_rating_no_reviews(self, product):
        assert product.average_rating == 0

    def test_average_rating_with_reviews(self, db, product, buyer, buyer2):
        from products.models import Review
        Review.objects.create(user=buyer, product=product, rating=4)
        Review.objects.create(user=buyer2, product=product, rating=2)
        product.refresh_from_db()
        assert product.average_rating == 3.0

    def test_in_stock_property_true(self, product, inventory):
        assert product.in_stock is True

    def test_in_stock_property_false(self, product, variant):
        from inventory.models import Inventory
        Inventory.objects.filter(variant=variant).delete()
        Inventory.objects.create(variant=variant, quantity_available=0)
        assert product.in_stock is False

    def test_str_repr(self, product):
        assert product.name in str(product)


# ─── ProductVariant Model ────────────────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.unit
class TestProductVariantModel:

    def test_discount_percent_calculated(self, variant):
        # variant has price=4999 compare_price=5999
        assert variant.discount_percent > 0

    def test_discount_percent_no_compare(self, product):
        from products.models import ProductVariant
        v = ProductVariant.objects.create(
            product=product, sku='NO-COMPARE-001',
            price=Decimal('999.00'), is_active=True,
        )
        assert v.discount_percent == 0

    def test_available_quantity_with_inventory(self, variant, inventory):
        assert variant.available_quantity == inventory.quantity_available

    def test_available_quantity_no_inventory(self, product):
        from products.models import ProductVariant
        v = ProductVariant.objects.create(
            product=product, sku='NO-INV-001',
            price=Decimal('500.00'), is_active=True,
        )
        assert v.available_quantity == 0

    def test_sku_unique_constraint(self, variant, product):
        from products.models import ProductVariant
        with pytest.raises(Exception):
            ProductVariant.objects.create(
                product=product, sku=variant.sku,   # duplicate
                price=Decimal('100.00'),
            )


# ─── Coupon Model ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.unit
class TestCouponModel:

    def test_is_valid_active_coupon(self, coupon):
        valid, msg = coupon.is_valid()
        assert valid is True

    def test_is_valid_expired_coupon(self, expired_coupon):
        valid, msg = expired_coupon.is_valid()
        assert valid is False
        assert 'expired' in msg.lower()

    def test_is_valid_inactive_coupon(self, coupon):
        coupon.is_active = False
        coupon.save(update_fields=['is_active'])
        valid, msg = coupon.is_valid()
        assert valid is False

    def test_usage_limit_exhausted(self, coupon):
        coupon.times_used = coupon.usage_limit
        coupon.save(update_fields=['times_used'])
        valid, msg = coupon.is_valid()
        assert valid is False
        assert 'limit' in msg.lower()

    def test_str_repr(self, coupon):
        assert coupon.code in str(coupon)


# ─── Inventory Model ─────────────────────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.unit
class TestInventoryModel:

    def test_quantity_sellable(self, inventory):
        # available=50, reserved=0
        assert inventory.quantity_sellable == 50

    def test_quantity_sellable_with_reservation(self, inventory):
        from inventory.models import Inventory
        Inventory.objects.filter(pk=inventory.pk).update(quantity_reserved=10)
        inventory.refresh_from_db()
        assert inventory.quantity_sellable == 40

    def test_quantity_sellable_never_negative(self, inventory):
        from inventory.models import Inventory
        # reserved > available — should clamp to 0
        Inventory.objects.filter(pk=inventory.pk).update(
            quantity_available=5, quantity_reserved=10,
        )
        inventory.refresh_from_db()
        assert inventory.quantity_sellable == 0

    def test_is_low_stock_below_threshold(self, inventory):
        from inventory.models import Inventory
        Inventory.objects.filter(pk=inventory.pk).update(
            quantity_available=3, low_stock_threshold=5,
        )
        inventory.refresh_from_db()
        assert inventory.is_low_stock is True

    def test_is_low_stock_above_threshold(self, inventory):
        # 50 available, threshold=5 → NOT low stock
        assert inventory.is_low_stock is False

    def test_str_repr(self, inventory):
        s = str(inventory)
        assert inventory.variant.sku in s


# ─── Cart Model ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.unit
class TestCartModel:

    def test_cart_subtotal_empty(self, buyer):
        from orders.models import Cart
        cart, _ = Cart.objects.get_or_create(user=buyer)
        assert cart.subtotal == 0

    def test_cart_subtotal_with_items(self, cart_with_item):
        # cart has 2 units at 4999 each
        assert cart_with_item.subtotal == Decimal('9998.00')

    def test_cart_discount_no_coupon(self, cart_with_item):
        assert cart_with_item.discount_amount == 0

    def test_cart_discount_with_percentage_coupon(self, cart_with_item, coupon):
        cart_with_item.coupon = coupon
        cart_with_item.save(update_fields=['coupon'])
        cart_with_item.refresh_from_db()
        discount = cart_with_item.discount_amount
        expected = cart_with_item.subtotal * Decimal('10') / 100
        assert discount == round(expected, 2)

    def test_cart_total_with_discount(self, cart_with_item, coupon):
        cart_with_item.coupon = coupon
        cart_with_item.save(update_fields=['coupon'])
        cart_with_item.refresh_from_db()
        assert cart_with_item.total == cart_with_item.subtotal - cart_with_item.discount_amount

    def test_cart_total_never_negative(self, cart_with_item):
        from products.models import Coupon
        mega_coupon = Coupon.objects.create(
            code='MEGA99',
            discount_type='fixed',
            discount_value=Decimal('99999.00'),
            min_order_value=Decimal('0.00'),
            is_active=True,
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=30),
        )
        cart_with_item.coupon = mega_coupon
        cart_with_item.save(update_fields=['coupon'])
        cart_with_item.refresh_from_db()
        assert cart_with_item.total >= 0


# ─── Order Model ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.unit
class TestOrderModel:

    def test_order_number_auto_generated(self, placed_order):
        assert placed_order.order_number.startswith('SG-')
        assert len(placed_order.order_number) == 13  # SG- + 10 hex chars

    def test_order_number_unique(self, buyer, variant, inventory, seller_profile):
        from orders.models import Order
        o1 = Order.objects.create(
            user=buyer, subtotal=Decimal('100'), total_price=Decimal('100'),
            shipping_name='A', shipping_phone='1', shipping_address_line1='X',
            shipping_city='Y', shipping_state='Z', shipping_pincode='123456',
        )
        o2 = Order.objects.create(
            user=buyer, subtotal=Decimal('200'), total_price=Decimal('200'),
            shipping_name='A', shipping_phone='1', shipping_address_line1='X',
            shipping_city='Y', shipping_state='Z', shipping_pincode='123456',
        )
        assert o1.order_number != o2.order_number

    def test_order_str_repr(self, placed_order):
        s = str(placed_order)
        assert placed_order.order_number in s


# ─── Seller Model ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
@pytest.mark.unit
class TestSellerModel:

    def test_seller_str_repr(self, seller_profile):
        assert seller_profile.store_name in str(seller_profile)

    def test_is_verified_flag(self, seller_profile, unverified_seller_profile):
        assert seller_profile.is_verified is True
        assert unverified_seller_profile.is_verified is False

    def test_verification_status(self, seller_profile, unverified_seller_profile):
        assert seller_profile.verification_status == 'approved'
        assert unverified_seller_profile.verification_status == 'pending'

    def test_store_name_unique(self, seller_profile, seller_user2):
        from sellers.models import Seller
        with pytest.raises(Exception):
            Seller.objects.create(
                user=seller_user2,
                store_name=seller_profile.store_name,   # duplicate
                is_verified=True,
            )

    def test_commission_rate_default(self, seller_profile):
        assert seller_profile.commission_rate == Decimal('10.00')
