from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, Count, F
from django.http import JsonResponse
from django.utils import timezone
from datetime import date, timedelta
from .models import InventoryItem, InventoryCategory, StockMovement


@login_required
def inventory_list(request):
    """List all inventory items with search and filter"""
    items = InventoryItem.objects.filter(is_active=True)
    
    # Search
    search = request.GET.get('search', '')
    if search:
        items = items.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(supplier__icontains=search) |
            Q(barcode__icontains=search)
        )
    
    # Filter by category
    category_id = request.GET.get('category', '')
    if category_id:
        items = items.filter(category_id=category_id)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        items = items.filter(status=status_filter)
    
    # Get categories for filter
    categories = InventoryCategory.objects.filter(items__is_active=True).distinct()
    
    # Summary stats
    total_items = items.count()
    low_stock_items = items.filter(status='low_stock').count()
    out_of_stock_items = items.filter(status='out_of_stock').count()
    total_value = items.aggregate(
        total=Sum('quantity') * Sum('unit_cost')
    )['total'] or 0
    
    context = {
        'items': items,
        'categories': categories,
        'total_items': total_items,
        'low_stock_items': low_stock_items,
        'out_of_stock_items': out_of_stock_items,
        'total_value': total_value,
        'search_query': search,
        'category_filter': category_id,
        'status_filter': status_filter,
    }
    return render(request, 'inventory/list.html', context)


@login_required
def inventory_add(request):
    """Add new inventory item"""
    categories = InventoryCategory.objects.all()
    
    if request.method == 'POST':
        try:
            # Get quantity and validate
            quantity = int(request.POST.get('quantity', 0))
            if quantity < 0:
                messages.error(request, 'Quantity cannot be negative')
                return render(request, 'inventory/add.html', {
                    'categories': categories,
                    'unit_choices': InventoryItem.UNIT_CHOICES,
                })
            
            # Create the item
            item = InventoryItem(
                name=request.POST.get('name'),
                description=request.POST.get('description', ''),
                category_id=request.POST.get('category') or None,
                quantity=quantity,
                unit=request.POST.get('unit', 'piece'),
                min_quantity=int(request.POST.get('min_quantity', 5)),
                unit_cost=float(request.POST.get('unit_cost', 0)),
                selling_price=float(request.POST.get('selling_price', 0)),
                supplier=request.POST.get('supplier', ''),
                supplier_contact=request.POST.get('supplier_contact', ''),
                barcode=request.POST.get('barcode', ''),
                location=request.POST.get('location', ''),
                notes=request.POST.get('notes', ''),
            )
            
            # Save the item (this will trigger the save method)
            item.save()
            
            # Create initial stock movement if quantity > 0
            if item.quantity > 0:
                StockMovement.objects.create(
                    item=item,
                    movement_type='purchase',
                    quantity=item.quantity,
                    previous_quantity=0,
                    new_quantity=item.quantity,
                    notes="Initial stock entry",
                    performed_by=request.user
                )
            
            messages.success(request, f'Item "{item.name}" added successfully!')
            return redirect('inventory:detail', pk=item.pk)
            
        except Exception as e:
            messages.error(request, f'Error adding item: {str(e)}')
            import traceback
            print(traceback.format_exc())
            return render(request, 'inventory/add.html', {
                'categories': categories,
                'unit_choices': InventoryItem.UNIT_CHOICES,
            })
    
    context = {
        'categories': categories,
        'unit_choices': InventoryItem.UNIT_CHOICES,
    }
    return render(request, 'inventory/add.html', context)

@login_required
def inventory_detail(request, pk):
    """View inventory item details with movement history"""
    item = get_object_or_404(InventoryItem, pk=pk)
    movements = item.movements.all()[:20]
    
    context = {
        'item': item,
        'movements': movements,
    }
    return render(request, 'inventory/detail.html', context)


@login_required
def inventory_edit(request, pk):
    """Edit inventory item"""
    item = get_object_or_404(InventoryItem, pk=pk)
    categories = InventoryCategory.objects.all()
    
    if request.method == 'POST':
        try:
            item.name = request.POST.get('name')
            item.description = request.POST.get('description', '')
            item.category_id = request.POST.get('category') or None
            item.unit = request.POST.get('unit', 'piece')
            item.min_quantity = int(request.POST.get('min_quantity', 5))
            max_qty = request.POST.get('max_quantity')
            item.max_quantity = int(max_qty) if max_qty else None
            item.unit_cost = float(request.POST.get('unit_cost', 0))
            item.selling_price = float(request.POST.get('selling_price', 0))
            item.supplier = request.POST.get('supplier', '')
            item.supplier_contact = request.POST.get('supplier_contact', '')
            item.barcode = request.POST.get('barcode', '')
            item.location = request.POST.get('location', '')
            item.notes = request.POST.get('notes', '')
            item.save()
            
            messages.success(request, f'Item "{item.name}" updated successfully!')
            return redirect('inventory:detail', pk=item.pk)
        except Exception as e:
            messages.error(request, f'Error updating item: {str(e)}')
    
    context = {
        'item': item,
        'categories': categories,
        'unit_choices': InventoryItem.UNIT_CHOICES,
    }
    return render(request, 'inventory/edit.html', context)


@login_required
def inventory_delete(request, pk):
    """Delete inventory item (soft delete)"""
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.method == 'POST':
        item.is_active = False
        item.save()
        messages.success(request, f'Item "{item.name}" has been archived.')
        return redirect('inventory:list')
    
    return render(request, 'inventory/delete.html', {'item': item})


@login_required
def inventory_adjust_stock(request, pk):
    """Adjust stock quantity (add or remove)"""
    item = get_object_or_404(InventoryItem, pk=pk)
    
    if request.method == 'POST':
        try:
            adjustment_type = request.POST.get('adjustment_type')
            quantity = int(request.POST.get('quantity', 0))
            notes = request.POST.get('notes', '')
            
            if quantity <= 0:
                messages.error(request, 'Quantity must be greater than 0')
                return redirect('inventory:detail', pk=item.pk)
            
            previous_quantity = item.quantity
            
            if adjustment_type == 'add':
                item.quantity += quantity
                movement_type = 'purchase'
                movement_notes = f"Added {quantity} units. {notes}"
            elif adjustment_type == 'remove':
                if quantity > item.quantity:
                    messages.error(request, f'Cannot remove more than available ({item.quantity})')
                    return redirect('inventory:detail', pk=item.pk)
                item.quantity -= quantity
                movement_type = 'sale'
                movement_notes = f"Removed {quantity} units. {notes}"
            else:
                messages.error(request, 'Invalid adjustment type')
                return redirect('inventory:detail', pk=item.pk)
            
            item.last_restocked = timezone.now()
            item.save()
            
            # Record movement
            StockMovement.objects.create(
                item=item,
                movement_type=movement_type,
                quantity=quantity if adjustment_type == 'add' else -quantity,
                previous_quantity=previous_quantity,
                new_quantity=item.quantity,
                notes=movement_notes,
                performed_by=request.user
            )
            
            messages.success(request, f'Stock adjusted successfully! New quantity: {item.quantity}')
        except Exception as e:
            messages.error(request, f'Error adjusting stock: {str(e)}')
    
    return redirect('inventory:detail', pk=item.pk)


@login_required
def inventory_low_stock(request):
    """View all low stock items"""
    items = InventoryItem.objects.filter(
        is_active=True,
        quantity__lte=F('min_quantity')
    ).order_by('quantity')
    
    context = {
        'items': items,
        'title': 'Low Stock Items',
    }
    return render(request, 'inventory/low_stock.html', context)


@login_required
def inventory_category_add(request):
    """Add a new category"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        if not name:
            messages.error(request, 'Category name is required')
            return redirect('inventory:category_add')
        
        category = InventoryCategory.objects.create(
            name=name,
            description=description
        )
        messages.success(request, f'Category "{category.name}" created successfully!')
        return redirect('inventory:list')
    
    return render(request, 'inventory/category_add.html')

@login_required
def inventory_dispense(request):
    """Quick dispense view for selling supplies to patients"""
    from billing.models import Invoice, InvoiceItem
    from patients.models import Patient
    
    if request.method == 'POST':
        try:
            patient_id = request.POST.get('patient')
            item_id = request.POST.get('item')
            quantity = int(request.POST.get('quantity', 1))
            notes = request.POST.get('notes', '')
            
            patient = get_object_or_404(Patient, pk=patient_id)
            item = get_object_or_404(InventoryItem, pk=item_id)
            
            # Check stock
            if item.quantity < quantity:
                messages.error(request, f'Not enough stock! Available: {item.quantity}')
                return redirect('inventory:dispense')
            
            # Create invoice for the supply
            invoice = Invoice.objects.create(
                invoice_number=f"DISP-{Invoice.objects.count() + 1:05d}",
                patient=patient,
                patient_name=patient.full_name,
                patient_phone=patient.phone,
                subtotal=quantity * item.selling_price,
                total_amount=quantity * item.selling_price,
                balance_due=quantity * item.selling_price,
                notes=f"Dispensed: {item.name} x{quantity}. {notes}",
                status='draft'
            )
            
            # Create invoice item
            InvoiceItem.objects.create(
                invoice=invoice,
                inventory_item=item,
                description=f"{item.name} - Dispensed",
                quantity=quantity,
                unit_price=item.selling_price,
                total_price=quantity * item.selling_price
            )
            
            # Update inventory
            item.quantity -= quantity
            item.save()
            
            # Record stock movement
            StockMovement.objects.create(
                item=item,
                movement_type='sale',
                quantity=-quantity,
                previous_quantity=item.quantity + quantity,
                new_quantity=item.quantity,
                reference_number=invoice.invoice_number,
                notes=f"Dispensed to {patient.full_name}. {notes}",
                performed_by=request.user
            )
            
            messages.success(request, f'Dispensed {quantity}x {item.name} to {patient.full_name}. Invoice #{invoice.invoice_number}')
            return redirect('billing:detail', pk=invoice.pk)
            
        except Exception as e:
            messages.error(request, f'Error dispensing: {str(e)}')
    
    patients = Patient.objects.filter(is_active=True)
    items = InventoryItem.objects.filter(is_active=True, quantity__gt=0)
    
    context = {
        'patients': patients,
        'items': items,
    }
    return render(request, 'inventory/dispense.html', context)

from django.http import JsonResponse
from django.db.models import Q

@login_required
def inventory_search_api(request):
    """API endpoint for searching inventory items"""
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    items = InventoryItem.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query) |
        Q(category__name__icontains=query)
    ).filter(
        is_active=True,
        quantity__gt=0
    )[:20]
    
    results = []
    for item in items:
        results.append({
            'id': item.id,
            'name': item.name,
            'quantity': item.quantity,
            'unit': item.get_unit_display(),
            'selling_price': float(item.selling_price),
            'category': item.category.name if item.category else 'Uncategorized',
        })
    
    return JsonResponse({'results': results})