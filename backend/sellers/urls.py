from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('', views.SellerListView.as_view(), name='seller-list'),
    path('<int:pk>/', views.SellerPublicDetailView.as_view(), name='seller-public'),

    # Seller self-service
    path('register/', views.SellerRegisterView.as_view(), name='seller-register'),
    path('profile/', views.SellerProfileView.as_view(), name='seller-profile'),
    path('bank/', views.SellerBankView.as_view(), name='seller-bank'),
    path('dashboard/', views.SellerDashboardView.as_view(), name='seller-dashboard'),
    path('dashboard/products/', views.SellerDashboardProductsView.as_view(), name='seller-dashboard-products'),
    path('orders/', views.SellerOrderItemListView.as_view(), name='seller-orders'),

    # Admin — seller verification
    path('admin/', views.AdminSellerListView.as_view(), name='admin-seller-list'),
    path('<int:pk>/verify/', views.AdminSellerVerifyView.as_view(), name='admin-seller-verify'),

    # Admin — return approval
    path('returns/', views.AdminReturnListView.as_view(), name='admin-return-list'),
    path('returns/<str:order_number>/review/', views.AdminReturnApprovalView.as_view(), name='admin-return-review'),
]
