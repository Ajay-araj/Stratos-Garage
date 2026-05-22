"""
Fix existing orders that were delivered/confirmed but have payment_status=pending.
Run: python fix_pending_payments.py

This is a one-time repair script for orders placed before the mark-paid fix.
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Stratosgarage.settings.development')
django.setup()

from orders.models import Order
from django.db.models import F

# Orders that have progressed past pending but payment was never confirmed
# These are orders where stock was deducted and work was done but payment_status is stuck
fixable_statuses = ['payment_confirmed', 'packed', 'shipped', 'out_for_delivery', 'delivered']

orders_to_fix = Order.objects.filter(
    payment_status='pending',
    order_status__in=fixable_statuses
)

print(f"Found {orders_to_fix.count()} orders with mismatched payment/order status:")
for o in orders_to_fix:
    print(f"  #{o.order_number} | order_status={o.order_status} | payment_status={o.payment_status} | total={o.total_price}")

if orders_to_fix.count() == 0:
    print("Nothing to fix.")
else:
    confirm = input("\nFix all of these? (yes/no): ").strip().lower()
    if confirm == 'yes':
        from sellers.models import Seller
        from orders.models import OrderItem, Notification

        for order in orders_to_fix:
            order.payment_status = 'completed'
            if order.order_status == 'pending':
                order.order_status = 'payment_confirmed'
            order.save(update_fields=['payment_status', 'order_status', 'updated_at'])

            # Create notification
            try:
                Notification.objects.create(
                    user=order.user,
                    notification_type='payment_success',
                    title=f"Payment Confirmed — Order #{order.order_number}",
                    message=f"Payment for order #{order.order_number} has been confirmed.",
                    related_order=order,
                )
            except Exception as e:
                print(f"  Warning: Could not create notification for {order.order_number}: {e}")

            print(f"  ✓ Fixed #{order.order_number}")

        print(f"\nFixed {orders_to_fix.count()} orders successfully.")
        print("Run the revenue diagnostic again to verify:")
        print("  python diagnose_revenue.py")
    else:
        print("Aborted.")
