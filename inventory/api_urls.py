from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'items', api_views.InventoryItemViewSet)
router.register(r'categories', api_views.InventoryCategoryViewSet)
router.register(r'movements', api_views.StockMovementViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('low-stock/', api_views.low_stock_items, name='low_stock'),
]
