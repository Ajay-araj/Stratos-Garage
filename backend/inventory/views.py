from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import F

from .models import Inventory, InventoryLog, StockReservation
from .serializers import (
    InventorySerializer, InventoryUpdateSerializer,
    InventoryLogSerializer, StockReservationSerializer,
)
from products.models import ProductVariant
from Stratosgarage.permissions import IsVerifiedSeller, IsAdminUser, IsVerifiedSellerOrBuyer


class VariantInventoryView(APIView):
    """GET/PATCH /api/inventory/<variant_id>/ — Seller manages own variant stock."""
    permission_classes = [IsAuthenticated, IsVerifiedSellerOrBuyer]

    def get(self, request, variant_id):
        variant = get_object_or_404(ProductVariant, pk=variant_id, product__seller__user=request.user)
        inventory, _ = Inventory.objects.get_or_create(
            variant=variant,
            defaults={'quantity_available': 0},
        )
        return Response(InventorySerializer(inventory).data)

    def patch(self, request, variant_id):
        variant = get_object_or_404(ProductVariant, pk=variant_id, product__seller__user=request.user)
        inventory, _ = Inventory.objects.get_or_create(
            variant=variant,
            defaults={'quantity_available': 0},
        )

        serializer = InventoryUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        new_qty = data.get('quantity_available')
        threshold = data.get('low_stock_threshold')
        notes = data.get('notes', '')

        if new_qty is not None:
            change = new_qty - inventory.quantity_available
            with transaction.atomic():
                inventory.quantity_available = new_qty
                inventory.save(update_fields=['quantity_available', 'last_updated'])
                InventoryLog.objects.create(
                    variant=variant,
                    change_quantity=change,
                    reason='restock' if change > 0 else 'manual_adjustment',
                    performed_by=request.user,
                    notes=notes,
                )

        if threshold is not None:
            inventory.low_stock_threshold = threshold
            inventory.save(update_fields=['low_stock_threshold'])

        inventory.refresh_from_db()
        return Response(InventorySerializer(inventory).data)


class InventoryLogListView(APIView):
    """GET /api/inventory/<variant_id>/logs/ — Audit log for a variant."""
    permission_classes = [IsAuthenticated, IsVerifiedSeller]

    def get(self, request, variant_id):
        variant = get_object_or_404(ProductVariant, pk=variant_id, product__seller__user=request.user)
        logs = (
            InventoryLog.objects
            .filter(variant=variant)
            .select_related('performed_by', 'reference_order')
            .order_by('-created_at')[:100]
        )
        return Response(InventoryLogSerializer(logs, many=True).data)


class InventoryBulkRestockView(APIView):
    """POST /api/inventory/restock/ — Bulk restock multiple variants."""
    permission_classes = [IsAuthenticated, IsVerifiedSeller]

    def post(self, request):
        """
        Body: [{"variant_id": 1, "quantity": 50, "notes": "..."}]
        """
        items = request.data
        if not isinstance(items, list) or not items:
            return Response({"error": "Provide a list of {variant_id, quantity}."}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        errors = []

        with transaction.atomic():
            for entry in items:
                variant_id = entry.get('variant_id')
                quantity = entry.get('quantity')
                notes = entry.get('notes', '')

                if not variant_id or quantity is None:
                    errors.append({"entry": entry, "error": "variant_id and quantity are required."})
                    continue

                try:
                    quantity = int(quantity)
                    if quantity <= 0:
                        raise ValueError()
                except (ValueError, TypeError):
                    errors.append({"entry": entry, "error": "quantity must be a positive integer."})
                    continue

                variant = ProductVariant.objects.filter(
                    pk=variant_id,
                    product__seller__user=request.user,
                ).first()

                if not variant:
                    errors.append({"entry": entry, "error": f"Variant {variant_id} not found or not yours."})
                    continue

                inventory, _ = Inventory.objects.get_or_create(
                    variant=variant,
                    defaults={'quantity_available': 0},
                )
                # Atomic increment — eliminates read-then-write race condition
                Inventory.objects.filter(pk=inventory.pk).update(
                    quantity_available=F('quantity_available') + quantity
                )
                inventory.refresh_from_db()

                InventoryLog.objects.create(
                    variant=variant,
                    change_quantity=quantity,
                    reason='restock',
                    performed_by=request.user,
                    notes=notes,
                )
                results.append({
                    "variant_id": variant_id,
                    "sku": variant.sku,
                    "new_quantity": inventory.quantity_available,
                })

        return Response({
            "restocked": results,
            "errors": errors,
        }, status=status.HTTP_200_OK if results else status.HTTP_400_BAD_REQUEST)


class LowStockAlertView(APIView):
    """GET /api/inventory/low-stock/ — Seller's low-stock variants."""
    permission_classes = [IsAuthenticated, IsVerifiedSeller]

    def get(self, request):
        inventories = (
            Inventory.objects
            .filter(
                variant__product__seller__user=request.user,
                variant__is_active=True,
            )
            .annotate(sellable=F('quantity_available') - F('quantity_reserved'))
            .filter(sellable__lte=F('low_stock_threshold'))
            .select_related('variant__product')
            .order_by('sellable')
        )
        data = [
            {
                "variant_id": inv.variant.id,
                "sku": inv.variant.sku,
                "product_name": inv.variant.product.name,
                "quantity_available": inv.quantity_available,
                "quantity_reserved": inv.quantity_reserved,
                "quantity_sellable": inv.quantity_sellable,
                "low_stock_threshold": inv.low_stock_threshold,
            }
            for inv in inventories
        ]
        return Response({"count": len(data), "results": data})
