"""
Run with: python manage.py shell < diagnose_revenue.py
Or:       python diagnose_revenue.py  (if Django setup is done)
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Stratosgarage.settings.development')
django.setup()

from orders.models import Order, OrderItem
from sellers.models import Seller

print("=" * 60)
print("REVENUE DIAGNOSTIC")
print("=" * 60)

# 1. All orders
orders = Order.objects.all().order_by('-created_at')[:10]
print(f"\n[1] Recent orders ({len(orders)} shown):")
for o in orders:
    print(f"  #{o.order_number} | order_status={o.order_status} | payment_status={o.payment_status} | total={o.total_price}")

# 2. All order items
items = OrderItem.objects.select_related('order', 'seller').all()[:20]
print(f"\n[2] Order Items ({len(items)} shown):")
for i in items:
    print(f"  item_id={i.id} | order={i.order.order_number} | seller={'NULL' if not i.seller else i.seller.store_name} | qty={i.quantity} | unit_price={i.unit_price} | order_payment={i.order.payment_status}")

# 3. PAID orders
paid = Order.objects.filter(payment_status='completed')
print(f"\n[3] Orders with payment_status='completed': {paid.count()}")
for o in paid:
    print(f"  #{o.order_number} | total={o.total_price}")

# 4. Items from paid orders
paid_items = OrderItem.objects.filter(order__payment_status='completed').select_related('seller')
print(f"\n[4] OrderItems from PAID orders: {paid_items.count()}")
for i in paid_items:
    print(f"  item={i.id} | seller={'NULL' if not i.seller else i.seller.store_name} | revenue={i.unit_price * i.quantity}")

# 5. All sellers
sellers = Seller.objects.all()
print(f"\n[5] Sellers: {sellers.count()}")
for s in sellers:
    print(f"  seller_id={s.id} | store={s.store_name} | user={s.user.username}")
    items_for_seller = OrderItem.objects.filter(seller=s)
    paid_items_for_seller = OrderItem.objects.filter(seller=s, order__payment_status='completed')
    print(f"    - Total order items: {items_for_seller.count()}")
    print(f"    - PAID order items:  {paid_items_for_seller.count()}")

# 6. Revenue calculation
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
for s in sellers:
    agg = OrderItem.objects.filter(seller=s, order__payment_status='completed').aggregate(
        revenue=Sum(ExpressionWrapper(F('unit_price') * F('quantity'), output_field=DecimalField(max_digits=14, decimal_places=2)))
    )
    print(f"\n[6] Revenue for '{s.store_name}': {agg['revenue'] or 0}")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
