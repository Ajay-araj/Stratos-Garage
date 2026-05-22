from django.urls import path
from . import views

urlpatterns = [
    path('initiate/', views.PaymentInitiateView.as_view(), name='payment-initiate'),
    path('verify/', views.PaymentVerifyView.as_view(), name='payment-verify'),
    path('webhook/razorpay/', views.RazorpayWebhookView.as_view(), name='payment-webhook-razorpay'),

    # Admin payout management — must come before <str:order_number>/ to avoid shadowing
    path('payouts/', views.AdminPayoutListView.as_view(), name='admin-payout-list'),
    path('payouts/<int:pk>/process/', views.PayoutProcessView.as_view(), name='payout-process'),
    path('payouts/seller/', views.SellerPayoutListView.as_view(), name='seller-payouts'),

    # Order-scoped
    path('<str:order_number>/', views.PaymentDetailView.as_view(), name='payment-detail'),
    path('<str:order_number>/refund/', views.RefundCreateView.as_view(), name='payment-refund'),
]
