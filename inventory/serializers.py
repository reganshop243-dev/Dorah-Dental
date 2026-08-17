from rest_framework import serializers
from .models import InventoryCategory, InventoryItem, StockMovement

class InventoryCategorySerializer(serializers.ModelSerializer):
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = InventoryCategory
        fields = '__all__'
    
    def get_item_count(self, obj):
        return obj.items.filter(is_active=True).count()

class InventoryItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    unit_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    total_value = serializers.SerializerMethodField()
    
    class Meta:
        model = InventoryItem
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_unit_display(self, obj):
        return dict(InventoryItem.UNIT_CHOICES).get(obj.unit, obj.unit)
    
    def get_status_display(self, obj):
        return dict(InventoryItem.STATUS_CHOICES).get(obj.status, obj.status)
    
    def get_total_value(self, obj):
        return obj.total_value

class StockMovementSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    movement_type_display = serializers.SerializerMethodField()
    performed_by_name = serializers.CharField(source='performed_by.get_full_name', read_only=True)
    
    class Meta:
        model = StockMovement
        fields = '__all__'
    
    def get_movement_type_display(self, obj):
        return dict(StockMovement.MOVEMENT_TYPES).get(obj.movement_type, obj.movement_type)
