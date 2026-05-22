from django.urls import path
from . import views

urlpatterns = [
    # Cart
    path('cart/', views.CartView.as_view(), name='cart-view'),
    path('cart/add/', views.CartAddView.as_view(), name='cart-add'),
    path('cart/clear/', views.CartClearView.as_view(), name='cart-clear'),
    path('cart/coupon/', views.CartApplyCouponView.as_view(), name='cart-coupon'),
    path('cart/<int:pk>/', views.CartItemUpdateView.as_view(), name='cart-item'),

    # Notifications — listed before <str:order_number>/ to avoid route collision
    path('notifications/', views.NotificationListView.as_view(), name='notifications'),
    path('notifications/mark-all-read/', views.NotificationMarkAllReadView.as_view(), name='notifications-mark-all'),
    path('notifications/<int:pk>/read/', views.NotificationMarkReadView.as_view(), name='notification-read'),

    # Seller Orders
    path('seller/orders/', views.SellerOrderListView.as_view(), name='seller-order-list'),
    path('seller/orders/<str:order_number>/status/', views.SellerOrderStatusView.as_view(), name='seller-order-status'),

    # Orders
    path('', views.OrderListView.as_view(), name='order-list'),
    path('place/', views.PlaceOrderView.as_view(), name='order-place'),
    path('<str:order_number>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('<str:order_number>/invoice/', views.OrderInvoiceView.as_view(), name='order-invoice'),
    path('<str:order_number>/cancel/', views.OrderCancelView.as_view(), name='order-cancel'),
    path('<str:order_number>/return/', views.ReturnRequestView.as_view(), name='order-return'),
    path('<str:order_number>/shipment/', views.ShipmentUpdateView.as_view(), name='order-shipment'),
    path('<str:order_number>/mark-paid/', views.MarkOrderPaidView.as_view(), name='order-mark-paid'),
]