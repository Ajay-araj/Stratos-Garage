from django.urls import path
from . import views

urlpatterns = [
    path('', views.WishlistView.as_view(), name='wishlist'),
    path('add/', views.WishlistAddView.as_view(), name='wishlist-add'),
    path('check/', views.WishlistCheckView.as_view(), name='wishlist-check'),
    path('clear/', views.WishlistClearView.as_view(), name='wishlist-clear'),
    path('<int:product_id>/', views.WishlistRemoveView.as_view(), name='wishlist-remove'),
]
