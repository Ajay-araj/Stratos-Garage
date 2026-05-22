from rest_framework import permissions


class IsSeller(permissions.BasePermission):
    """Allows access only to users with role='seller'."""
    message = "Only verified sellers can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == 'seller'
        )


class IsSellerOrReadOnly(permissions.BasePermission):
    """Read-only for everyone; write only for sellers."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == 'seller'
        )


class IsProductOwner(permissions.BasePermission):
    """Only the seller who owns the product can modify it."""
    message = "You do not own this product."

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        try:
            return obj.seller.user == request.user
        except AttributeError:
            return False


class IsOrderOwner(permissions.BasePermission):
    """Only the order's buyer can access it."""
    message = "You do not own this order."

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsAdminUser(permissions.BasePermission):
    """Admin-only access."""
    message = "Admin access required."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role == 'admin' or request.user.is_staff)
        )


class IsVerifiedSeller(permissions.BasePermission):
    """Only approved sellers."""
    message = "Your seller account must be approved before performing this action."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.role == 'seller'):
            return False
        try:
            return request.user.seller_profile.is_verified
        except AttributeError:
            return False

class IsVerifiedSellerOrBuyer(permissions.BasePermission):
    """
    Allows any authenticated user whose email is verified AND whose role is
    'seller' or 'buyer'. We intentionally do NOT check seller_profile.is_verified
    here — that strict check belongs only on financial/payout endpoints
    (use IsVerifiedSeller for those). Product creation auto-creates the Seller
    stub, so the DB record may not exist yet when this permission runs.
    """
    message = "You must be a verified seller or a buyer to perform this action."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_email_verified):
            return False
        return user.role in ('seller', 'buyer')
