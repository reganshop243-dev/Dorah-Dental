from django.contrib import admin
from .models import InventoryCategory, InventoryItem, StockMovement

@admin.register(InventoryCategory)
class InventoryCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'quantity', 'unit', 'status', 'unit_cost', 'selling_price']
    list_filter = ['category', 'status', 'unit', 'is_active']
    search_fields = ['name', 'description', 'barcode', 'supplier']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category')
        }),
        ('Stock Information', {
            'fields': ('quantity', 'unit', 'min_quantity', 'max_quantity')
        }),
        ('Pricing', {
            'fields': ('unit_cost', 'selling_price')
        }),
        ('Supplier Information', {
            'fields': ('supplier', 'supplier_contact')
        }),
        ('Additional Info', {
            'fields': ('barcode', 'location', 'notes', 'is_active')
        }),
        ('System Fields', {
            'fields': ('status', 'created_at', 'updated_at', 'last_restocked'),
            'classes': ('collapse',)
        }),
    )

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['item', 'movement_type', 'quantity', 'previous_quantity', 'new_quantity', 'created_at']
    list_filter = ['movement_type', 'created_at']
    search_fields = ['item__name', 'reference_number']
    readonly_fields = ['created_at']
