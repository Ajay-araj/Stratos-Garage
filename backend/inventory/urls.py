from django.urls import path
from . import views

urlpatterns = [
    path('restock/', views.InventoryBulkRestockView.as_view(), name='inventory-restock'),
    path('low-stock/', views.LowStockAlertView.as_view(), name='inventory-low-stock'),
    path('<int:variant_id>/', views.VariantInventoryView.as_view(), name='inventory-detail'),
    path('<int:variant_id>/logs/', views.InventoryLogListView.as_view(), name='inventory-logs'),
]
