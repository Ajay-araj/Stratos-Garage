import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, Q, F, ExpressionWrapper, DecimalField

from .models import Seller
from .serializers import SellerSerializer, SellerRegisterSerializer, SellerBankSerializer, SellerPublicSerializer
from Stratosgarage.permissions import IsSeller, IsVerifiedSeller, IsAdminUser, IsVerifiedSellerOrBuyer
from orders.models import Order, OrderItem
from inventory.models import Inventory, InventoryLog

logger = logging.getLogger(__name__)


class SellerRegisterView(APIView):
    """POST /api/sellers/register/ — Create seller profile."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if hasattr(request.user, 'seller_profile'):
            return Response(
                {'error': 'Seller profile already exists.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = SellerRegisterSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            seller = serializer.save()
            return Response(
                {'message': 'Seller profile created. Pending approval.', 'seller': SellerSerializer(seller).data},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SellerProfileView(APIView):
    """GET/PATCH /api/sellers/profile/ — Own seller profile."""
    permission_classes = [IsAuthenticated, IsVerifiedSeller]

    def get(self, request):
        seller = get_object_or_404(Seller, user=request.user)
        return Response(SellerSerializer(seller).data)

    def patch(self, request):
        seller = get_object_or_404(Seller, user=request.user)
        serializer = SellerSerializer(seller, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SellerBankView(APIView):
    """PATCH /api/sellers/bank/ — Update bank details."""
    permission_classes = [IsAuthenticated, IsVerifiedSeller]

    def patch(self, request):
        seller = get_object_or_404(Seller, user=request.user)
        serializer = SellerBankSerializer(seller, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Bank details updated.', 'data': serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SellerPublicDetailView(APIView):
    """GET /api/sellers/<id>/ — Public store page."""
    permission_classes = [AllowAny]

    def get(self, request, pk):
        seller = get_object_or_404(Seller.objects.prefetch_related('products'), pk=pk)
        return Response(SellerPublicSerializer(seller).data)


class SellerDashboardView(APIView):
    """GET /api/sellers/dashboard/ — Aggregated stats."""
    permission_classes = [IsAuthenticated, IsVerifiedSeller]

    def get(self, request):
        seller = get_object_or_404(Seller, user=request.user)

        product_stats = seller.products.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
        )
        
        # Calculate Pending Orders (from order__order_status='pending' and not cancelled)
        pending_orders = OrderItem.objects.filter(seller=seller, order__order_status='pending').values('order').distinct().count()

        # Calculate Total Revenue (only PAID orders)
        revenue_agg = OrderItem.objects.filter(seller=seller, order__payment_status='completed').aggregate(
            revenue=Sum(ExpressionWrapper(F('unit_price') * F('quantity'), output_field=DecimalField(max_digits=14, decimal_places=2)))
        )
        total_revenue = revenue_agg['revenue'] or 0

        # Calculate Products Sold (non-cancelled and non-pending orders)
        sold_agg = OrderItem.objects.filter(seller=seller).exclude(order__order_status__in=['cancelled', 'pending']).aggregate(
            sold=Sum('quantity')
        )
        products_sold = sold_agg['sold'] or 0

        return Response({
            'store_name': seller.store_name,
            'is_verified': seller.is_verified,
            'verification_status': seller.verification_status,
            'total_products': product_stats['total'],
            'active_products': product_stats['active'],
            'pending_orders': pending_orders,
            'total_revenue': str(total_revenue),
            'products_sold': products_sold,
        })

class SellerDashboardProductsView(APIView):
    """GET /api/sellers/dashboard/products/ — Get recent products."""
    permission_classes = [IsAuthenticated, IsVerifiedSellerOrBuyer]

    def get(self, request):
        try:
            seller = request.user.seller_profile
        except Exception:
            return Response([])
        
        products = seller.products.prefetch_related('variants__inventory', 'category', 'images').order_by('-created_at')[:10]
        data = [
            {
                "id": p.id,
                "slug": p.slug,
                "name": p.name,
                "category": p.category.name if p.category else 'Uncategorized',
                "price": str(p.base_price),
                "stock": sum(getattr(v.inventory, 'quantity_available', 0) for v in p.variants.all() if hasattr(v, 'inventory')),
                "variant_id": p.variants.first().id if p.variants.exists() else None,
                "seller": p.seller.store_name,
                "created_at": p.created_at.strftime('%Y-%m-%d'),
                "image": p.primary_image or None,
                "is_active": p.is_active
            }
            for p in products
        ]
        return Response(data)


class SellerListView(APIView):
    """GET /api/sellers/ — Public list of verified sellers."""
    permission_classes = [AllowAny]

    def get(self, request):
        sellers = Seller.objects.filter(is_verified=True).order_by('-total_sales')
        return Response(SellerPublicSerializer(sellers, many=True).data)


class SellerOrderItemListView(APIView):
    """GET /api/sellers/orders/ — Seller views their own order items."""
    permission_classes = [IsAuthenticated, IsVerifiedSeller]

    def get(self, request):
        seller = get_object_or_404(Seller, user=request.user)
        order_status_filter = request.query_params.get('order_status', '')
        qs = (
            OrderItem.objects
            .filter(seller=seller)
            .select_related('order', 'variant__product')
            .order_by('-order__created_at')
        )
        if order_status_filter:
            qs = qs.filter(order__order_status=order_status_filter)

        data = [
            {
                'order_item_id': item.id,
                'order_number': item.order.order_number,
                'order_status': item.order.order_status,
                'payment_status': item.order.payment_status,
                'product_name': item.product_name,
                'variant_sku': item.variant_sku,
                'quantity': item.quantity,
                'unit_price': str(item.unit_price),
                'subtotal': str(item.subtotal),
                'return_status': item.return_status,
                'created_at': item.order.created_at,
            }
            for item in qs
        ]
        return Response({'count': len(data), 'results': data})


# ─── Admin: Seller Verification ───────────────────────────────────────────────

class AdminSellerVerifyView(APIView):
    """POST /api/sellers/<pk>/verify/ — Admin approves or rejects a seller."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, pk):
        seller = get_object_or_404(Seller, pk=pk)
        action = request.data.get('action', '').strip().lower()

        if action not in ('approve', 'reject', 'suspend'):
            return Response(
                {'error': "action must be one of: approve, reject, suspend"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action == 'approve':
            seller.verification_status = 'approved'
            seller.is_verified = True
        elif action == 'reject':
            seller.verification_status = 'rejected'
            seller.is_verified = False
        elif action == 'suspend':
            seller.verification_status = 'suspended'
            seller.is_verified = False

        seller.save(update_fields=['verification_status', 'is_verified', 'updated_at'])
        logger.info(f"Seller {seller.store_name} (pk={pk}) {action}d by admin {request.user.username}")

        return Response({
            'message': f"Seller '{seller.store_name}' has been {action}d.",
            'seller': SellerSerializer(seller).data,
        })


class AdminSellerListView(APIView):
    """GET /api/sellers/admin/ — Admin lists all sellers with optional status filter."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        v_status = request.query_params.get('status', '')
        qs = Seller.objects.select_related('user').order_by('-created_at')
        if v_status:
            qs = qs.filter(verification_status=v_status)
        return Response(SellerSerializer(qs, many=True).data)


# ─── Admin: Return Approval ───────────────────────────────────────────────────

class AdminReturnApprovalView(APIView):
    """POST /api/sellers/returns/<order_number>/review/ — Admin approves/rejects return."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number)

        if order.order_status != 'return_requested':
            return Response(
                {'error': 'Order is not in return_requested status.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        action = request.data.get('action', '').strip().lower()
        if action not in ('approve', 'reject'):
            return Response(
                {'error': "action must be 'approve' or 'reject'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.db import transaction as db_tx
        with db_tx.atomic():
            if action == 'approve':
                order.order_status = 'returned'
                order.save(update_fields=['order_status', 'updated_at'])
                order.items.all().update(return_status='approved')

                # Restore inventory
                for item in order.items.select_related('variant').all():
                    if item.variant:
                        from django.db.models import F
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

                from orders.models import Notification
                Notification.objects.create(
                    user=order.user,
                    notification_type='general',
                    title=f"Return Approved — Order #{order.order_number}",
                    message="Your return has been approved. Refund will be processed within 5-7 business days.",
                    related_order=order,
                )
            else:
                order.order_status = 'delivered'  # Revert to delivered
                order.save(update_fields=['order_status', 'updated_at'])
                order.items.all().update(return_status='rejected')

                from orders.models import Notification
                Notification.objects.create(
                    user=order.user,
                    notification_type='general',
                    title=f"Return Rejected — Order #{order.order_number}",
                    message="Unfortunately your return request has been rejected.",
                    related_order=order,
                )

        return Response({
            'message': f"Return {action}d for order #{order_number}.",
            'order_status': order.order_status,
        })


class AdminReturnListView(APIView):
    """GET /api/sellers/returns/ — Admin views all pending return requests."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        orders = (
            Order.objects
            .filter(order_status='return_requested')
            .prefetch_related('items')
            .select_related('user')
            .order_by('-updated_at')
        )
        data = [
            {
                'order_number': o.order_number,
                'user': o.user.username,
                'total_price': str(o.total_price),
                'return_reasons': list({i.return_reason for i in o.items.all() if i.return_reason}),
                'updated_at': o.updated_at,
            }
            for o in orders
        ]
        return Response({'count': len(data), 'results': data})
