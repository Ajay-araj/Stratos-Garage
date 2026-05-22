from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Auth
    path('auth/register/', views.RegisterView.as_view(), name='user-register'),
    path('auth/login/', views.ThrottledTokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('auth/logout/', views.LogoutView.as_view(), name='user-logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # New Auth Flow
    path('auth/verify-otp/', views.VerifyOTPView.as_view(), name='verify-otp'),
    path('auth/resend-otp/', views.ResendOTPView.as_view(), name='resend-otp'),
    path('auth/create-password/', views.CreatePasswordView.as_view(), name='create-password'),

    # Profile
    path('profile/', views.ProfileView.as_view(), name='user-profile'),
    path('profile/change-password/', views.ChangePasswordView.as_view(), name='change-password'),

    # Password Reset
    path('auth/forgot-password/', views.ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/reset-password/', views.ResetPasswordView.as_view(), name='reset-password'),

    # Addresses
    path('addresses/', views.AddressListCreateView.as_view(), name='address-list'),
    path('addresses/<int:pk>/', views.AddressDetailView.as_view(), name='address-detail'),
]
