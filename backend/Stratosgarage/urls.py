from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from Stratosgarage.health import HealthCheckView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Health check (no auth required)
    path('api/health/', HealthCheckView.as_view(), name='health-check'),

    # OpenAPI schema + Swagger UI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Auth & Users
    path('api/users/', include('users.urls')),

    # Sellers
    path('api/sellers/', include('sellers.urls')),

    # Products (catalog, variants, reviews, coupons)
    path('api/products/', include('products.urls')),

    # Inventory
    path('api/inventory/', include('inventory.urls')),

    # Cart, Orders & Notifications
    path('api/orders/', include('orders.urls')),

    # Payments
    path('api/payments/', include('payments.urls')),

    # Wishlist
    path('api/wishlist/', include('wishlist.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
