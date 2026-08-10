from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Main inventory
    path('', views.inventory_list, name='list'),
    path('add/', views.inventory_add, name='add'),
    path('<int:pk>/', views.inventory_detail, name='detail'),
    path('<int:pk>/edit/', views.inventory_edit, name='edit'),
    path('<int:pk>/delete/', views.inventory_delete, name='delete'),
    path('<int:pk>/adjust-stock/', views.inventory_adjust_stock, name='adjust_stock'),
    path('dispense/', views.inventory_dispense, name='dispense'),
    # Low stock
    path('low-stock/', views.inventory_low_stock, name='low_stock'),
    path('api/search/', views.inventory_search_api, name='search_api'),
    # Categories
    path('category/add/', views.inventory_category_add, name='category_add'),
]