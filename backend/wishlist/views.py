from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Wishlist, WishlistItem
from .serializers import WishlistSerializer
from products.models import Product


class WishlistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        wishlist_qs = (
            Wishlist.objects
            .prefetch_related(
                'items__product__seller',
                'items__product__category',
                'items__product__images',
                'items__product__variants__inventory',
            )
            .get(pk=wishlist.pk)
        )
        return Response(WishlistSerializer(wishlist_qs, context={'request': request}).data)


class WishlistAddView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({"error": "product_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        product = get_object_or_404(Product, pk=product_id, is_active=True)
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        _, created = WishlistItem.objects.get_or_create(wishlist=wishlist, product=product)
        if not created:
            return Response({"message": "Product already in wishlist."}, status=status.HTTP_200_OK)
        return Response({"message": "Added to wishlist.", "product_id": product.id}, status=status.HTTP_201_CREATED)


class WishlistRemoveView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, product_id):
        wishlist = get_object_or_404(Wishlist, user=request.user)
        item = get_object_or_404(WishlistItem, wishlist=wishlist, product_id=product_id)
        item.delete()
        return Response({"message": "Removed from wishlist."}, status=status.HTTP_204_NO_CONTENT)


class WishlistClearView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
        count, _ = wishlist.items.all().delete()
        return Response({"message": f"Wishlist cleared. {count} item(s) removed."})


class WishlistCheckView(APIView):
    """GET /api/wishlist/check/?product_id=<id> — Quick check if product is wishlisted."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        product_id = request.query_params.get('product_id')
        if not product_id:
            return Response({"error": "product_id query param required."}, status=status.HTTP_400_BAD_REQUEST)
        wishlist = Wishlist.objects.filter(user=request.user).first()
        in_wishlist = False
        if wishlist:
            in_wishlist = wishlist.items.filter(product_id=product_id).exists()
        return Response({"product_id": product_id, "in_wishlist": in_wishlist})
