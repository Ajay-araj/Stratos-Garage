"""
Run: python diagnose_cart.py
Checks backend cart state for all users.
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Stratosgarage.settings.development')
django.setup()

from orders.models import Cart, CartItem
from django.contrib.auth import get_user_model
User = get_user_model()

print("=" * 60)
print("CART DIAGNOSTIC")
print("=" * 60)

carts = Cart.objects.prefetch_related('items__variant').select_related('user').all()
print(f"\nTotal Carts: {carts.count()}")
for cart in carts:
    items = list(cart.items.all())
    print(f"\n  User: {cart.user.username}")
    print(f"  Cart ID: {cart.id}")
    print(f"  Items count: {len(items)}")
    for item in items:
        print(f"    - variant_id={item.variant_id} | qty={item.quantity} | added={item.added_at}")

from inventory.models import StockReservation
from django.utils import timezone
active_res = StockReservation.objects.filter(is_released=False)
expired_res = active_res.filter(expires_at__lt=timezone.now())
print(f"\nActive Reservations: {active_res.count()}")
print(f"Expired (not released): {expired_res.count()}")

print("\n" + "=" * 60)
