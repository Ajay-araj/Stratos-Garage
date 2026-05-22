"""
Shared pytest fixtures for Stratos Garage test suite.
All fixtures use transactional rollback — no test-to-test leakage.
"""
import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


# ─── API Client ───────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


# ─── Users ───────────────────────────────────────────────────────────────────

@pytest.fixture
def buyer(db, django_user_model):
    return django_user_model.objects.create_user(
        username='buyer1', email='buyer1@test.com',
        password='TestPass123!', role='buyer',
    )


@pytest.fixture
def buyer2(db, django_user_model):
    return django_user_model.objects.create_user(
        username='buyer2', email='buyer2@test.com',
        password='TestPass123!', role='buyer',
    )


@pytest.fixture
def seller_user(db, django_user_model):
    return django_user_model.objects.create_user(
        username='seller1', email='seller1@test.com',
        password='TestPass123!', role='seller',
    )


@pytest.fixture
def seller_user2(db, django_user_model):
    """A second seller — used to test cross-seller isolation."""
    return django_user_model.objects.create_user(
        username='seller2', email='seller2@test.com',
        password='TestPass123!', role='seller',
    )


@pytest.fixture
def unverified_seller_user(db, django_user_model):
    return django_user_model.objects.create_user(
        username='unverified_seller', email='unverified@test.com',
        password='TestPass123!', role='seller',
    )


@pytest.fixture
def admin_user(db, django_user_model):
    return django_user_model.objects.create_user(
        username='admin1', email='admin1@test.com',
        password='TestPass123!', role='admin', is_staff=True,
    )


# ─── Sellers ─────────────────────────────────────────────────────────────────

@pytest.fixture
def seller_profile(db, seller_user):
    from sellers.models import Seller
    return Seller.objects.create(
        user=seller_user,
        store_name='Test Moto Store',
        store_description='Best bike parts.',
        verification_status='approved',
        is_verified=True,
        commission_rate=Decimal('10.00'),
    )


@pytest.fixture
def seller_profile2(db, seller_user2):
    """Second verified seller — isolation tests."""
    from sellers.models import Seller
    return Seller.objects.create(
        user=seller_user2,
        store_name='Rival Moto Store',
        verification_status='approved',
        is_verified=True,
        commission_rate=Decimal('10.00'),
    )


@pytest.fixture
def unverified_seller_profile(db, unverified_seller_user):
    from sellers.models import Seller
    return Seller.objects.create(
        user=unverified_seller_user,
        store_name='Pending Moto Store',
        verification_status='pending',
        is_verified=False,
        commission_rate=Decimal('10.00'),
    )


# ─── Products ─────────────────────────────────────────────────────────────────

@pytest.fixture
def category(db):
    from products.models import Category
    return Category.objects.create(name='Exhausts', slug='exhausts')


@pytest.fixture
def category2(db):
    from products.models import Category
    return Category.objects.create(name='Brakes', slug='brakes')


@pytest.fixture
def product(db, seller_profile, category):
    from products.models import Product
    return Product.objects.create(
        seller=seller_profile, category=category,
        name='Racing Exhaust Pro', slug='racing-exhaust-pro',
        base_price=Decimal('4999.00'), is_active=True,
    )


@pytest.fixture
def product2(db, seller_profile2, category2):
    """Product belonging to the rival seller."""
    from products.models import Product
    return Product.objects.create(
        seller=seller_profile2, category=category2,
        name='Carbon Brake Pad', slug='carbon-brake-pad',
        base_price=Decimal('2499.00'), is_active=True,
    )


@pytest.fixture
def attribute_type(db):
    from products.models import AttributeType
    return AttributeType.objects.create(
        name='material', slug='material', display_name='Material'
    )


@pytest.fixture
def variant(db, product, attribute_type):
    from products.models import ProductVariant, VariantAttribute
    v = ProductVariant.objects.create(
        product=product, sku='EXH-RACE-001',
        price=Decimal('4999.00'), compare_price=Decimal('5999.00'),
        is_active=True,
    )
    VariantAttribute.objects.create(
        variant=v, attribute_type=attribute_type, value='Stainless Steel'
    )
    return v


@pytest.fixture
def variant2(db, product2):
    """Variant belonging to the rival seller's product."""
    from products.models import ProductVariant
    return ProductVariant.objects.create(
        product=product2, sku='BRK-CARB-001',
        price=Decimal('2499.00'), is_active=True,
    )


@pytest.fixture
def inventory(db, variant):
    from inventory.models import Inventory
    return Inventory.objects.create(
        variant=variant, quantity_available=50, quantity_reserved=0,
        low_stock_threshold=5,
    )


@pytest.fixture
def inventory2(db, variant2):
    from inventory.models import Inventory
    return Inventory.objects.create(
        variant=variant2, quantity_available=20, quantity_reserved=0,
    )


@pytest.fixture
def bike_compat(db):
    from products.models import BikeCompatibility
    return BikeCompatibility.objects.create(
        brand='Royal Enfield', model='Himalayan', year_from=2020,
    )


@pytest.fixture
def coupon(db):
    from products.models import Coupon
    return Coupon.objects.create(
        code='SAVE10',
        discount_type='percentage',
        discount_value=Decimal('10.00'),
        min_order_value=Decimal('0.00'),
        usage_limit=100,
        per_user_limit=1,
        is_active=True,
        valid_from=timezone.now() - timedelta(days=1),
        valid_until=timezone.now() + timedelta(days=30),
    )


@pytest.fixture
def expired_coupon(db):
    from products.models import Coupon
    return Coupon.objects.create(
        code='EXPIRED',
        discount_type='fixed',
        discount_value=Decimal('200.00'),
        min_order_value=Decimal('0.00'),
        is_active=True,
        valid_from=timezone.now() - timedelta(days=60),
        valid_until=timezone.now() - timedelta(days=1),
    )


# ─── Authenticated Clients ───────────────────────────────────────────────────

@pytest.fixture
def buyer_client(api_client, buyer):
    token = RefreshToken.for_user(buyer)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    api_client._buyer = buyer
    return api_client


@pytest.fixture
def buyer2_client(buyer2):
    client = APIClient()
    token = RefreshToken.for_user(buyer2)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    client._buyer = buyer2
    return client


@pytest.fixture
def seller_client(api_client, seller_user, seller_profile):
    token = RefreshToken.for_user(seller_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    api_client._seller_user = seller_user
    api_client._seller = seller_profile
    return api_client


@pytest.fixture
def seller2_client(seller_user2, seller_profile2):
    client = APIClient()
    token = RefreshToken.for_user(seller_user2)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    client._seller_user = seller_user2
    client._seller = seller_profile2
    return client


@pytest.fixture
def unverified_seller_client(api_client, unverified_seller_user, unverified_seller_profile):
    token = RefreshToken.for_user(unverified_seller_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    token = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    api_client._admin = admin_user
    return api_client


# ─── Cart / Order Helpers ─────────────────────────────────────────────────────

@pytest.fixture
def cart_with_item(db, buyer, variant, inventory):
    from orders.models import Cart, CartItem
    from inventory.models import StockReservation, Inventory as Inv
    cart, _ = Cart.objects.get_or_create(user=buyer)
    item = CartItem.objects.create(cart=cart, variant=variant, quantity=2)
    expires_at = timezone.now() + timedelta(minutes=30)
    StockReservation.objects.create(
        variant=variant, cart_item=item,
        quantity_reserved=2, expires_at=expires_at,
    )
    Inv.objects.filter(pk=inventory.pk).update(quantity_reserved=2)
    return cart


@pytest.fixture
def placed_order(db, buyer, variant, inventory, seller_profile):
    from orders.models import Order, OrderItem
    from inventory.models import Inventory as Inv
    order = Order.objects.create(
        user=buyer,
        subtotal=Decimal('9998.00'),
        total_price=Decimal('9998.00'),
        shipping_name='Test Buyer',
        shipping_phone='9876543210',
        shipping_address_line1='123 Test Street',
        shipping_city='Mumbai',
        shipping_state='Maharashtra',
        shipping_pincode='400001',
    )
    OrderItem.objects.create(
        order=order, variant=variant, seller=seller_profile,
        product_name=variant.product.name, variant_sku=variant.sku,
        quantity=2, unit_price=variant.price,
    )
    Inv.objects.filter(pk=inventory.pk).update(quantity_available=48)
    return order


@pytest.fixture
def delivered_order(placed_order):
    placed_order.order_status = 'delivered'
    placed_order.payment_status = 'completed'
    placed_order.save(update_fields=['order_status', 'payment_status', 'updated_at'])
    return placed_order


@pytest.fixture
def completed_payment(db, placed_order, buyer):
    """A completed Razorpay payment linked to placed_order."""
    from payments.models import Payment
    placed_order.payment_status = 'completed'
    placed_order.order_status = 'confirmed'
    placed_order.save(update_fields=['payment_status', 'order_status', 'updated_at'])
    return Payment.objects.create(
        order=placed_order,
        user=buyer,
        payment_gateway='razorpay',
        gateway_order_id='order_TEST123456',
        gateway_payment_id='pay_TEST789',
        amount=placed_order.total_price,
        currency='INR',
        status='completed',
    )
