from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.invoice_list, name='list'),
    path('add/', views.invoice_add, name='add'),
    path('<int:pk>/', views.invoice_detail, name='detail'),
    path('<int:pk>/payment/', views.add_payment, name='add_payment'),
    path('<int:pk>/print/', views.print_invoice, name='print'),
    path('<int:pk>/delete/', views.invoice_delete, name='delete'),
    path('<int:pk>/add-item/', views.add_invoice_item, name='add_invoice_item'),
    path('<int:pk>/remove-item/<int:item_pk>/', views.remove_invoice_item, name='remove_invoice_item'),
    path('store-cart/', views.store_cart, name='store_cart'),
    
    # Expenses
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.expense_add, name='expense_add'),
    path('expenses/<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),
    
    # Balance Sheet
    path('balance-sheet/', views.balance_sheet, name='balance_sheet'),
]