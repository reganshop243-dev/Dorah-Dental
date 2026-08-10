
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.contrib.auth.models import User


class InventoryCategory(models.Model):
    """Category for inventory items"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Inventory Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    UNIT_CHOICES = [
        ('piece', 'Piece'),
        ('box', 'Box'),
        ('pack', 'Pack'),
        ('carton', 'Carton'),
        ('set', 'Set'),
        ('pair', 'Pair'),
        ('roll', 'Roll'),
        ('bottle', 'Bottle'),
        ('tube', 'Tube'),
        ('vial', 'Vial'),
        ('syringe', 'Syringe'),
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('ml', 'Milliliter'),
        ('l', 'Liter'),
        ('meter', 'Meter'),
        ('cm', 'Centimeter'),
        ('sheet', 'Sheet'),
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('discontinued', 'Discontinued'),
    ]
    
    # Basic information
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(InventoryCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')
    
    # Stock information
    quantity = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='piece')
    min_quantity = models.PositiveIntegerField(default=5, help_text="Minimum quantity before low stock alert")
    max_quantity = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum quantity to keep in stock")
    
    # Pricing
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Cost per unit")
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Selling price per unit")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    is_active = models.BooleanField(default=True)
    
    # Supplier information
    supplier = models.CharField(max_length=200, blank=True, null=True)
    supplier_contact = models.CharField(max_length=100, blank=True, null=True)
    
    # Additional info
    barcode = models.CharField(max_length=100, blank=True, null=True, unique=True)
    location = models.CharField(max_length=100, blank=True, null=True, help_text="Storage location")
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_restocked = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.quantity} {self.get_unit_display()})"
    
    @property
    def total_value(self):
        """Calculate total value of stock"""
        return self.quantity * self.unit_cost
    
    @property
    def is_low_stock(self):
        """Check if item is low on stock"""
        return self.quantity <= self.min_quantity and self.quantity > 0
    
    @property
    def is_out_of_stock(self):
        """Check if item is out of stock"""
        return self.quantity == 0
    
    def update_status(self):
        """Update status based on quantity"""
        if self.quantity <= 0:
            self.status = 'out_of_stock'
        elif self.quantity <= self.min_quantity:
            self.status = 'low_stock'
        else:
            self.status = 'available'
    
    def save(self, *args, **kwargs):
        """Update status before saving"""
        # Update status based on quantity
        self.update_status()
        
        # Set last_restocked if quantity > 0 and it's a new item or quantity increased
        if self.quantity > 0:
            if self.pk is None:  # New item
                self.last_restocked = timezone.now()
            else:
                # Check if quantity increased - only if we're not in a recursion loop
                try:
                    old = InventoryItem.objects.get(pk=self.pk)
                    if self.quantity > old.quantity:
                        self.last_restocked = timezone.now()
                except InventoryItem.DoesNotExist:
                    pass
        
        super().save(*args, **kwargs)


class StockMovement(models.Model):
    """Track stock movements (additions, removals, adjustments)"""
    MOVEMENT_TYPES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('adjustment', 'Adjustment'),
        ('return', 'Return'),
        ('transfer', 'Transfer'),
        ('waste', 'Waste'),
        ('donation', 'Donation'),
    ]
    
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField(help_text="Positive for additions, negative for removals")
    previous_quantity = models.PositiveIntegerField()
    new_quantity = models.PositiveIntegerField()
    reference_number = models.CharField(max_length=100, blank=True, null=True, help_text="Invoice or order number")
    notes = models.TextField(blank=True, null=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.item.name} ({self.quantity})"