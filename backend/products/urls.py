from django.urls import path
from . import views

urlpatterns = [
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category-tree'),
    path('categories/flat/', views.CategoryFlatListView.as_view(), name='category-flat'),

    # Products
    path('', views.ProductListView.as_view(), name='product-list'),
    path('add/', views.ProductCreateView.as_view(), name='product-create'),

    # Attributes
    path('attributes/types/', views.AttributeTypeListView.as_view(), name='attribute-types'),

    # Bike Compatibility
    path('bikes/compatibility/', views.BikeCompatibilityListView.as_view(), name='bike-compat'),
    path('bikes/compatibility/add/', views.BikeCompatibilityCreateView.as_view(), name='bike-compat-add'),

    # Coupons
    path('coupons/', views.CouponListCreateView.as_view(), name='coupon-list'),
    path('coupons/validate/', views.CouponValidateView.as_view(), name='coupon-validate'),

    # Product detail & management (slug-based — must come after specific prefix routes)
    path('<slug:slug>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('<slug:slug>/manage/', views.ProductManageView.as_view(), name='product-manage'),
    path('<slug:slug>/archive/', views.ProductArchiveView.as_view(), name='product-archive'),
    path('<slug:slug>/delete/', views.ProductDeleteView.as_view(), name='product-delete'),
    path('<slug:slug>/images/', views.ProductImageUploadView.as_view(), name='product-images'),
    path('<slug:slug>/bikes/', views.ProductBikeCompatibilityView.as_view(), name='product-bikes'),

    # Variants
    path('<slug:slug>/variants/', views.VariantListCreateView.as_view(), name='variant-list'),
    path('variants/<int:variant_id>/', views.VariantManageView.as_view(), name='variant-manage'),

    # Reviews
    path('<slug:slug>/reviews/', views.ReviewListCreateView.as_view(), name='review-list'),
    path('<slug:slug>/reviews/<int:pk>/helpful/', views.ReviewHelpfulView.as_view(), name='review-helpful'),
]
