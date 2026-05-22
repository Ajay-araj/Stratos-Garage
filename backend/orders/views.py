import logging
from datetime import timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import BasicAuthentication
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import Cart, CartItem, Order, OrderItem, Notification, Shipment
from .serializers import (
    CartSerializer, CartItemSerializer, OrderSerializer,
    ShippingAddressSerializer, NotificationSerializer, ShipmentSerializer,
)
from products.models import Product, ProductVariant, Coupon
from inventory.models import Inventory, InventoryLog, StockReservation
from sellers.models import Seller as SellerModel

logger = logging.getLogger(__name__)

CART_RESERVATION_MINUTES = 30


def _notify(user, notification_type, title, message, order=None):
    Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        related_order=order,
    )


def _release_cart_item_reservations(cart_item):
    """Release all active reservations for a cart item; decrement inventory.quantity_reserved."""
    reservations = StockReservation.objects.filter(
        cart_item=cart_item,
        is_released=False,
    )
    total_released = sum(r.quantity_reserved for r in reservations)
    if total_released:
        reservations.update(is_released=True)
        Inventory.objects.filter(variant=cart_item.variant).update(
            quantity_reserved=F('quantity_reserved') - total_released
        )


# ─── Cart ─────────────────────────────────────────────────────────────────────

class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_qs = Cart.objects.prefetch_related(
            'items__variant__product__images',
            'items__variant__inventory',
            'items__variant__attributes__attribute_type',
            'coupon',
        ).get(pk=cart.pk)
        return Response(CartSerializer(cart_qs, context={'request': request}).data)


class CartAddView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        variant_id = request.data.get('variant_id')
        product_id = request.data.get('product_id')
        
        try:
            quantity = int(request.data.get('quantity', 1))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid quantity.'}, status=status.HTTP_400_BAD_REQUEST)

        if not variant_id and not product_id:
            return Response({'error': 'variant_id or product_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if quantity < 1:
            return Response({'error': 'Quantity must be at least 1.'}, status=status.HTTP_400_BAD_REQUEST)

        if variant_id:
            variant = get_object_or_404(ProductVariant, pk=variant_id, is_active=True)
        else:
            product = get_object_or_404(Product, pk=product_id, is_active=True)
            variant = product.variants.filter(is_active=True).first()
            if not variant:
                return Response({'error': 'No variants available for this product.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            inventory = Inventory.objects.select_for_update().filter(variant=variant).first()
            if not inventory:
                return Response({'error': 'Inventory record not found for this variant.'}, status=status.HTTP_400_BAD_REQUEST)

            cart, _ = Cart.objects.get_or_create(user=request.user)
            existing_item = CartItem.objects.filter(cart=cart, variant=variant).first()
            existing_qty = existing_item.quantity if existing_item else 0

            # Find existing active reservation for this user/cart/variant
            existing_reservation = None
            existing_reserved_qty = 0
            if existing_item:
                existing_reservation = StockReservation.objects.select_for_update().filter(
                    cart_item=existing_item,
                    is_released=False,
                    expires_at__gt=timezone.now(),
                ).first()
                existing_reserved_qty = existing_reservation.quantity_reserved if existing_reservation else 0

            desired_total_qty = existing_qty + quantity
            # Effective available = physical stock minus OTHER users' reservations
            effective_available = inventory.quantity_available - inventory.quantity_reserved + existing_reserved_qty

            if effective_available < desired_total_qty:
                return Response(
                    {'error': f'Only {effective_available} units available.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            expires_at = timezone.now() + timedelta(minutes=CART_RESERVATION_MINUTES)

            if existing_item:
                existing_item.quantity = desired_total_qty
                existing_item.save(update_fields=['quantity'])
                item = existing_item

                if existing_reservation:
                    qty_diff = desired_total_qty - existing_reserved_qty
                    existing_reservation.quantity_reserved = desired_total_qty
                    existing_reservation.expires_at = expires_at
                    existing_reservation.save(update_fields=['quantity_reserved', 'expires_at'])
                    Inventory.objects.filter(pk=inventory.pk).update(
                        quantity_reserved=F('quantity_reserved') + qty_diff
                    )
                else:
                    # Previous reservation expired — create fresh one
                    StockReservation.objects.create(
                        variant=variant, cart_item=item,
                        quantity_reserved=desired_total_qty, expires_at=expires_at,
                    )
                    Inventory.objects.filter(pk=inventory.pk).update(
                        quantity_reserved=F('quantity_reserved') + desired_total_qty
                    )
            else:
                item = CartItem.objects.create(cart=cart, variant=variant, quantity=quantity)
                StockReservation.objects.create(
                    variant=variant, cart_item=item,
                    quantity_reserved=quantity, expires_at=expires_at,
                )
                Inventory.objects.filter(pk=inventory.pk).update(
                    quantity_reserved=F('quantity_reserved') + quantity
                )

        return Response(CartItemSerializer(item).data, status=status.HTTP_200_OK)


class CartItemUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        cart = get_object_or_404(Cart, user=request.user)
        item = get_object_or_404(CartItem, pk=pk, cart=cart)
        try:
            quantity = int(request.data.get('quantity', item.quantity))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid quantity.'}, status=status.HTTP_400_BAD_REQUEST)

        if quantity < 1:
            return Response({'error': 'Quantity must be at least 1.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            inventory = Inventory.objects.select_for_update().filter(variant=item.variant).first()
            if not inventory:
                return Response({'error': 'Inventory not found.'}, status=status.HTTP_400_BAD_REQUEST)

            existing_reservation = StockReservation.objects.select_for_update().filter(
                cart_item=item, is_released=False, expires_at__gt=timezone.now()
            ).first()
            existing_reserved_qty = existing_reservation.quantity_reserved if existing_reservation else 0

            effective_available = inventory.quantity_available - inventory.quantity_reserved + existing_reserved_qty
            if effective_available < quantity:
                return Response(
                    {'error': f'Only {effective_available} units available.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            qty_diff = quantity - existing_reserved_qty
            expires_at = timezone.now() + timedelta(minutes=CART_RESERVATION_MINUTES)

            if existing_reservation:
                existing_reservation.quantity_reserved = quantity
                existing_reservation.expires_at = expires_at
                existing_reservation.save(update_fields=['quantity_reserved', 'expires_at'])
            else:
                StockReservation.objects.create(
                    variant=item.variant, cart_item=item,
                    quantity_reserved=quantity, expires_at=expires_at,
                )

            Inventory.objects.filter(pk=inventory.pk).update(
                quantity_reserved=F('quantity_reserved') + qty_diff
            )
            item.quantity = quantity
            item.save(update_fields=['quantity'])

        return Response(CartItemSerializer(item).data)

    def delete(self, request, pk):
        cart = get_object_or_404(Cart, user=request.user)
        item = get_object_or_404(CartItem, pk=pk, cart=cart)
        with transaction.atomic():
            _release_cart_item_reservations(item)
            item.delete()
        # 200 OK with body — 204 must carry no body (RFC 7231)
        return Response({'message': 'Item removed from cart.'}, status=status.HTTP_200_OK)


class CartClearView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        with transaction.atomic():
            for item in cart.items.select_related('variant').all():
                _release_cart_item_reservations(item)
            cart.items.all().delete()
        return Response({'message': 'Cart cleared.'})


class CartApplyCouponView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get('code', '').strip().upper()
        cart, _ = Cart.objects.get_or_create(user=request.user)

        if not code:
            cart.coupon = None
            cart.save(update_fields=['coupon'])
            return Response({'message': 'Coupon removed.'})

        coupon = get_object_or_404(Coupon, code=code)
        valid, msg = coupon.is_valid()
        if not valid:
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)

        used_times = Order.objects.filter(user=request.user, coupon=coupon).count()
        if used_times >= coupon.per_user_limit:
            return Response({'error': 'You have already used this coupon.'}, status=status.HTTP_400_BAD_REQUEST)

        cart.coupon = coupon
        cart.save(update_fields=['coupon'])
        return Response({'message': f"Coupon '{code}' applied.", 'discount': str(cart.discount_amount)})


# ─── Orders ───────────────────────────────────────────────────────────────────

class PlaceOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            shipping_serializer = ShippingAddressSerializer(data=request.data)
            if not shipping_serializer.is_valid():
                return Response(shipping_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            cart = get_object_or_404(
                Cart.objects.prefetch_related(
                    'items__variant__inventory',
                    'items__variant__product__seller',
                    'items__variant__product__images',
                    'items__variant__attributes__attribute_type',
                    'coupon',
                ),
                user=request.user,
            )
            
            # Use prefetched items instead of making a new query which can cause JOIN issues
            items = list(cart.items.all())

            if not items:
                return Response({'error': 'Your cart is empty.'}, status=status.HTTP_400_BAD_REQUEST)

            payment_method_input = request.data.get('payment_method', 'razorpay')

            with transaction.atomic():
                # Lock all inventories atomically before any write
                variant_ids = [item.variant_id for item in items]
                locked_inventories = {
                    inv.variant_id: inv
                    for inv in Inventory.objects.select_for_update().filter(variant_id__in=variant_ids)
                }

                # Re-validate stock under the lock
                for item in items:
                    inv = locked_inventories.get(item.variant_id)
                    sellable = inv.quantity_sellable if inv else 0
                    if not inv or sellable < item.quantity:
                        transaction.set_rollback(True)
                        return Response(
                            {'error': f"Only {sellable} units of '{item.variant.product.name}' available."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                subtotal = cart.subtotal
                discount = cart.discount_amount
                total = cart.total
                shipping = shipping_serializer.validated_data

                expected_delivery_date = timezone.now().date() + timedelta(days=5)

                order_kwargs = {
                    'user': request.user,
                    'coupon': cart.coupon,
                    'coupon_code': cart.coupon.code if cart.coupon else '',
                    'coupon_discount': discount,
                    'subtotal': subtotal,
                    'total_price': total,
                    'expected_delivery': expected_delivery_date,
                }
                
                if payment_method_input == 'cod':
                    order_kwargs['payment_method'] = 'COD'
                    order_kwargs['payment_status'] = 'PENDING'
                    order_kwargs['order_status'] = 'Pending'

                order = Order.objects.create(**order_kwargs, **shipping)

                for item in items:
                    product = item.variant.product
                    seller = product.seller
                    image_url = ''
                    # Use prefetch cache — do NOT call .filter() which bypasses prefetch
                    product_images = list(product.images.all())
                    primary_img = (
                        next((img for img in product_images if img.is_primary), None)
                        or (product_images[0] if product_images else None)
                    )
                    if primary_img:
                        try:
                            image_url = request.build_absolute_uri(primary_img.image.url)
                        except Exception:
                            image_url = ''

                    # Use prefetch cache — .all() hits cache; .select_related() would bypass it
                    attr_str = ', '.join(
                        f"{va.attribute_type.display_name}: {va.value}"
                        for va in item.variant.attributes.all()
                    )

                    OrderItem.objects.create(
                        order=order,
                        variant=item.variant,
                        seller=seller,
                        product_name=product.name,
                        variant_sku=item.variant.sku,
                        variant_description=attr_str,
                        product_image=image_url,
                        quantity=item.quantity,
                        unit_price=item.variant.price,
                    )

                    # Atomic deduction under the select_for_update lock
                    inv = locked_inventories[item.variant_id]
                    Inventory.objects.filter(pk=inv.pk).update(
                        quantity_available=F('quantity_available') - item.quantity,
                        quantity_reserved=F('quantity_reserved') - item.quantity,
                    )

                    InventoryLog.objects.create(
                        variant=item.variant,
                        change_quantity=-item.quantity,
                        reason='purchase',
                        reference_order=order,
                        performed_by=request.user,
                    )

                    # Release stock reservations for this cart item
                    StockReservation.objects.filter(
                        cart_item=item, is_released=False
                    ).update(is_released=True)

                    # Seller sales logic moved to MarkOrderPaidView

                # Update coupon usage
                if cart.coupon:
                    Coupon.objects.filter(pk=cart.coupon.pk).update(
                        times_used=F('times_used') + 1
                    )

                # Clear cart
                cart.items.all().delete()
                cart.coupon = None
                cart.save(update_fields=['coupon'])

            # Prepare summary strings for emails
            items_summary_buyer = "<br>".join(
                f"{item.quantity}x {item.variant.product.name} (₹{item.variant.price})" for item in items
            )
            shipping_address_str = f"{order.shipping_address_line1}, {order.shipping_city}, {order.shipping_state} {order.shipping_pincode}"

            try:
                from users.tasks import send_order_confirmation_email_task, send_seller_new_order_email_task
                send_order_confirmation_email_task.delay(
                    user_email=request.user.email,
                    first_name=request.user.username,
                    order_id=order.order_number,
                    order_total=str(order.total_price),
                    items_summary=items_summary_buyer + f"<br><br><b>Expected Delivery:</b> {order.expected_delivery.strftime('%d %B %Y')}" if order.expected_delivery else items_summary_buyer,
                )

                # Notify each seller
                seller_items = {}
                for item in items:
                    seller = item.variant.product.seller
                    if seller not in seller_items:
                        seller_items[seller] = []
                    seller_items[seller].append(item)

                for seller, s_items in seller_items.items():
                    s_summary = "<br>".join(f"{i.quantity}x {i.variant.product.name}" for i in s_items)
                    send_seller_new_order_email_task.delay(
                        seller_email=seller.user.email,
                        seller_store_name=seller.store_name,
                        buyer_name=request.user.username,
                        order_id=order.order_number,
                        items_summary=s_summary,
                        shipping_address=shipping_address_str,
                    )
            except Exception as e:
                logger.error(f"Failed to queue emails: {e}")

            logger.info(f"Order {order.order_number} placed by {request.user.username}")
            _notify(
                request.user, 'order_placed',
                f"Order #{order.order_number} Placed!",
                f"Your order has been placed successfully. Total: ₹{order.total_price}",
                order=order,
            )
            return Response(
                {
                    'success': True,
                    'message': 'Order Placed Successfully',
                    'order': OrderSerializer(
                        Order.objects.prefetch_related('items', 'shipment').get(pk=order.pk)
                    ).data,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            print(e)
            return Response(
                {"error": "Unable to place order"},
                status=500
            )


class OrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = (
            Order.objects
            .filter(user=request.user)
            .prefetch_related('items', 'shipment')
            .order_by('-created_at')
        )
        return Response(OrderSerializer(orders, many=True).data)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_number):
        order = get_object_or_404(
            Order.objects.prefetch_related('items', 'shipment'),
            order_number=order_number,
            user=request.user,
        )
        return Response(OrderSerializer(order).data)


class OrderCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        if order.order_status not in ('pending', 'payment_confirmed'):
            return Response(
                {'error': 'Only pending or confirmed orders can be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            order.order_status = 'cancelled'
            order.save(update_fields=['order_status', 'updated_at'])

            for item in order.items.select_related('variant').all():
                if item.variant:
                    Inventory.objects.filter(variant=item.variant).update(
                        quantity_available=F('quantity_available') + item.quantity
                    )
                    InventoryLog.objects.create(
                        variant=item.variant,
                        change_quantity=item.quantity,
                        reason='return',
                        reference_order=order,
                        performed_by=request.user,
                    )

        _notify(
            request.user, 'order_cancelled',
            f"Order #{order.order_number} Cancelled",
            "Your order has been cancelled and stock restored.",
            order=order,
        )
        try:
            from users.tasks import send_order_status_email_task
            send_order_status_email_task.delay(
                user_email=request.user.email,
                first_name=request.user.username,
                order_id=order.order_number,
                status='cancelled',
                message='Your order has been cancelled successfully. Any applicable refunds will be processed soon.'
            )
        except Exception as e:
            logger.error(f"Failed to queue cancellation email: {e}")
        return Response({'message': 'Order cancelled.', 'order': OrderSerializer(order).data})


class ReturnRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        if order.order_status != 'delivered':
            return Response(
                {'error': 'Only delivered orders can be returned.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reason = request.data.get('reason', '').strip()
        if not reason:
            return Response({'error': 'Return reason is required.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            order.order_status = 'return_requested'
            order.save(update_fields=['order_status', 'updated_at'])
            order.items.all().update(return_status='requested', return_reason=reason)

        return Response({'message': 'Return request submitted.', 'order': OrderSerializer(order).data})


# ─── Seller Orders ──────────────────────────────────────────────────────────────

class SellerOrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, 'role', '') != 'seller' or not hasattr(request.user, 'seller_profile'):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        
        orders = (
            Order.objects
            .filter(items__seller=request.user.seller_profile)
            .distinct()
            .prefetch_related('items', 'shipment')
            .order_by('-created_at')
        )
        return Response(OrderSerializer(orders, many=True).data)


class SellerOrderStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, order_number):
        if getattr(request.user, 'role', '') != 'seller' or not hasattr(request.user, 'seller_profile'):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
            
        # Get order
        orders = Order.objects.filter(order_number=order_number, items__seller=request.user.seller_profile).distinct()
        if not orders.exists():
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        order = orders.first()
        
        new_status = request.data.get('status')
        valid_statuses = [choice[0] for choice in Order.ORDER_STATUS]
        
        if new_status in valid_statuses:
            if new_status == 'payment_confirmed' and order.payment_status != 'completed':
                order.payment_status = 'completed'
                order.save(update_fields=['payment_status'])
                
            advanced_statuses = ['packed', 'shipped', 'out_for_delivery', 'delivered']
            if new_status in advanced_statuses and order.payment_status != 'completed':
                return Response(
                    {'error': f'Cannot update order status to {new_status}. Payment must be completed first.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            old_status = order.order_status
            order.order_status = new_status
            
            if old_status != 'cancelled' and new_status == 'cancelled':
                # Restore stock ONLY ONCE
                with transaction.atomic():
                    for item in order.items.select_related('variant').all():
                        if item.variant:
                            Inventory.objects.filter(variant=item.variant).update(
                                quantity_available=F('quantity_available') + item.quantity
                            )
                            InventoryLog.objects.create(
                                variant=item.variant,
                                change_quantity=item.quantity,
                                reason='manual_adjustment',
                                reference_order=order,
                                performed_by=request.user,
                            )
            
            order.save(update_fields=['order_status', 'updated_at'])
            
            # Send specific emails if marked packed/shipped/delivered
            if new_status in ['packed', 'shipped', 'delivered']:
                message_map = {
                    'packed': 'Your order is packed and ready to be shipped.',
                    'shipped': 'Your order is on the way.',
                    'delivered': 'Your order has been delivered. Enjoy your ride!'
                }
                
                _notify(order.user, f'order_{new_status}', f"Order #{order.order_number} {new_status.capitalize()}!", message_map[new_status], order=order)
                
                try:
                    from users.tasks import send_order_status_email_task
                    send_order_status_email_task.delay(
                        user_email=order.user.email,
                        first_name=order.user.username,
                        order_id=order.order_number,
                        status=new_status,
                        message=message_map[new_status]
                    )
                except Exception as e:
                    logger.error(f"Failed to queue status update email: {e}")
            elif new_status == 'cancelled':
                _notify(order.user, 'order_cancelled', f"Order #{order.order_number} Cancelled", "Your order has been cancelled by the seller.", order=order)
                try:
                    from users.tasks import send_order_status_email_task
                    send_order_status_email_task.delay(
                        user_email=order.user.email, first_name=order.user.username, order_id=order.order_number, status='cancelled', message='Your order has been cancelled.'
                    )
                except Exception as e:
                    pass

            return Response(OrderSerializer(order).data)
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)


# ─── Shipment ─────────────────────────────────────────────────────────────────

class ShipmentUpdateView(APIView):
    """PATCH /api/orders/<order_number>/shipment/ — Seller creates/updates shipment."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, order_number):
        order = get_object_or_404(
            Order.objects
            .select_related('user')
            .prefetch_related('items__seller'),
            order_number=order_number,
        )

        is_admin = request.user.is_staff or request.user.role == 'admin'
        is_seller_owner = (
            request.user.role == 'seller'
            and hasattr(request.user, 'seller_profile')
            and order.items.filter(seller=request.user.seller_profile).exists()
        )

        if not (is_admin or is_seller_owner):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        shipment, _ = Shipment.objects.get_or_create(
            order=order,
            defaults={
                'tracking_number': request.data.get('tracking_number', ''),
                'carrier': request.data.get('carrier', 'other'),
            }
        )
        serializer = ShipmentSerializer(shipment, data=request.data, partial=True)
        if serializer.is_valid():
            shipment = serializer.save()
            
            if shipment.status == 'delivered' and order.order_status != 'delivered':
                if order.payment_status != 'completed':
                    return Response({'error': 'Cannot mark shipment as delivered for unpaid orders.'}, status=status.HTTP_400_BAD_REQUEST)
                order.order_status = 'delivered'
                order.save(update_fields=['order_status', 'updated_at'])
                _notify(
                    order.user, 'order_delivered',
                    f"Order #{order.order_number} Delivered!",
                    "Your order has been delivered. Enjoy your ride!",
                    order=order,
                )
            elif shipment.status == 'in_transit' and order.order_status == 'payment_confirmed':
                order.order_status = 'shipped'
                order.save(update_fields=['order_status', 'updated_at'])
                _notify(
                    order.user, 'order_shipped',
                    f"Order #{order.order_number} Shipped!",
                    f"Tracking: {shipment.tracking_number} via {shipment.get_carrier_display()}",
                    order=order,
                )
            return Response(ShipmentSerializer(shipment).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ─── Notifications ────────────────────────────────────────────────────────────

class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = (
            request.user.notifications
            .select_related('related_order')
            .order_by('-created_at')[:50]
        )
        return Response(NotificationSerializer(notifications, many=True).data)


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.is_read = True
        notif.save(update_fields=['is_read'])
        return Response({'message': 'Marked as read.'})


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = request.user.notifications.filter(is_read=False).update(is_read=True)
        return Response({'message': f"{updated} notification(s) marked as read."})


# ─── Demo Payment ─────────────────────────────────────────────────────────────

class MarkOrderPaidView(APIView):
    """
    Public endpoint for the demo QR scanner to mark an order as PAID.
    Simulates external webhook/payment gateway callback.
    authentication_classes = [] bypasses CSRF — SessionAuthentication enforces CSRF for
    authenticated sessions, so we remove it here for this public webhook-style endpoint.
    """
    authentication_classes = []  # Bypass CSRF — no session auth for this public endpoint
    permission_classes = [AllowAny]

    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number)
        
        if order.payment_status != 'completed':
            order.payment_status = 'completed'
            if order.order_status == 'pending':
                order.order_status = 'payment_confirmed'
            order.save(update_fields=['payment_status', 'order_status', 'updated_at'])
            
            # Update total sales and revenue for seller
            seller_totals = {}
            seller_quantities = {}
            for item in order.items.select_related('seller').all():
                if item.seller:
                    seller_totals[item.seller.pk] = seller_totals.get(item.seller.pk, 0) + item.subtotal
                    seller_quantities[item.seller.pk] = seller_quantities.get(item.seller.pk, 0) + item.quantity
            
            for seller_pk in seller_totals.keys():
                SellerModel.objects.filter(pk=seller_pk).update(
                    total_sales=F('total_sales') + seller_totals[seller_pk],
                    products_sold=F('products_sold') + seller_quantities[seller_pk]
                )

            _notify(
                order.user, 'payment_success',
                f"Payment Successful!",
                f"Payment for Order #{order.order_number} has been received.",
                order=order,
            )
            
        return Response({'message': 'Order marked as paid successfully'})

from django.http import HttpResponse

class OrderInvoiceView(APIView):
    """GET /api/orders/<order_number>/invoice/ — Generate PDF Invoice."""
    permission_classes = [IsAuthenticated]

    def get(self, request, order_number):
        order = get_object_or_404(Order.objects.prefetch_related('items__seller'), order_number=order_number, user=request.user)
        if order.payment_status != 'completed':
            return Response({'error': 'Invoice is only available for paid orders.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
        except ImportError:
            return Response({'error': 'PDF generation library not installed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Invoice_{order.order_number}.pdf"'
        
        doc = SimpleDocTemplate(response, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        elements.append(Paragraph(f"<b>INVOICE - STRATOS GARAGE</b>", styles['Title']))
        elements.append(Spacer(1, 12))
        
        elements.append(Paragraph(f"<b>Order ID:</b> {order.order_number}", styles['Normal']))
        elements.append(Paragraph(f"<b>Date:</b> {order.created_at.strftime('%Y-%m-%d')}", styles['Normal']))
        elements.append(Paragraph(f"<b>Payment Status:</b> {order.get_payment_status_display()}", styles['Normal']))
        elements.append(Paragraph(f"<b>Expected Delivery:</b> {order.expected_delivery.strftime('%Y-%m-%d') if order.expected_delivery else 'TBA'}", styles['Normal']))
        elements.append(Spacer(1, 12))
        
        buyer_info = f"<b>Buyer:</b><br/>Name: {order.shipping_name}<br/>Phone: {order.shipping_phone}<br/>Address: {order.shipping_address_line1}, {order.shipping_city}, {order.shipping_state} {order.shipping_pincode}"
        elements.append(Paragraph(buyer_info, styles['Normal']))
        elements.append(Spacer(1, 12))
        
        sellers = list({item.seller.store_name for item in order.items.all() if item.seller})
        seller_info = f"<b>Seller(s):</b> {', '.join(sellers)}"
        elements.append(Paragraph(seller_info, styles['Normal']))
        elements.append(Spacer(1, 12))
        
        data = [['Item', 'Qty', 'Unit Price', 'Subtotal']]
        for item in order.items.all():
            data.append([item.product_name, str(item.quantity), f"INR {item.unit_price}", f"INR {item.subtotal}"])
            
        data.append(['', '', 'Subtotal', f"INR {order.subtotal}"])
        data.append(['', '', 'Shipping', "INR 0.00"])
        if order.coupon_discount > 0:
            data.append(['', '', 'Discount', f"-INR {order.coupon_discount}"])
        data.append(['', '', 'Total', f"INR {order.total_price}"])
        
        table = Table(data, colWidths=[250, 50, 100, 100])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
        
        doc.build(elements)
        return response