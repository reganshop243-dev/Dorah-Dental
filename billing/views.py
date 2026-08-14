from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.utils import timezone
from django.http import JsonResponse
from .models import Invoice, InvoiceItem, Payment, Expense
from patients.models import Patient
from appointments.models import Appointment, Service
import json


@login_required
def invoice_list(request):
    """List all invoices"""
    invoices = Invoice.objects.all().order_by('-issue_date')
    return render(request, 'billing/invoice_list.html', {'invoices': invoices})


@login_required
def invoice_add(request):
    """Add a new invoice with items from cart"""
    from inventory.models import InventoryItem
    from django.db import transaction
    
    if request.method == 'POST':
        try:
            # Debug: Print all POST data
            print("=" * 60)
            print("POST DATA RECEIVED:")
            for key, value in request.POST.items():
                print(f"  {key}: {value[:100] if len(str(value)) > 100 else value}")
            print("=" * 60)
            
            patient_id = request.POST.get('patient')
            cart_items_json = request.POST.get('cart_items', '[]')
            issue_date = request.POST.get('issue_date', '')
            
            # Try to get cart items from session if POST doesn't have it
            if not cart_items_json or cart_items_json == '[]':
                cart_items_json = request.session.get('cart_items', '[]')
                print(f"Using session cart data: {cart_items_json}")
            
            # Parse cart items
            try:
                cart_items = json.loads(cart_items_json)
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}")
                cart_items = []
            
            print(f"Parsed cart items: {cart_items}")
            print(f"Number of items: {len(cart_items)}")
            
            if not patient_id:
                messages.error(request, 'Please select a patient')
                return redirect('billing:add')
            
            if not cart_items or len(cart_items) == 0:
                messages.error(request, 'Please add at least one item to the invoice')
                return redirect('billing:add')
            
            patient = get_object_or_404(Patient, pk=patient_id)
            
            # Generate invoice number
            last_invoice = Invoice.objects.order_by('-id').first()
            if last_invoice:
                invoice_number = f"INV-{last_invoice.id + 1:05d}"
            else:
                invoice_number = "INV-00001"
            
            with transaction.atomic():
                # Calculate subtotal
                subtotal = 0
                for item in cart_items:
                    price = float(item.get('price', 0))
                    quantity = int(item.get('quantity', 1))
                    subtotal += price * quantity
                
                tax_rate = float(request.POST.get('tax_rate', 0))
                discount = float(request.POST.get('discount', 0))
                tax_amount = (subtotal * tax_rate) / 100 if tax_rate > 0 else 0
                total_amount = subtotal + tax_amount - discount
                
                # Handle backdated issue date
                if issue_date:
                    try:
                        from datetime import datetime
                        issue_datetime = datetime.strptime(issue_date, '%Y-%m-%d')
                        issue_date_obj = timezone.make_aware(issue_datetime)
                    except:
                        issue_date_obj = timezone.now()
                else:
                    issue_date_obj = timezone.now()
                
                # Create invoice
                invoice = Invoice.objects.create(
                    invoice_number=invoice_number,
                    patient=patient,
                    patient_name=patient.full_name,
                    patient_phone=patient.phone,
                    subtotal=subtotal,
                    tax_rate=tax_rate,
                    tax_amount=tax_amount,
                    discount=discount,
                    total_amount=total_amount,
                    amount_paid=0,
                    balance_due=total_amount,
                    notes=request.POST.get('notes', ''),
                    due_date=request.POST.get('due_date') or None,
                    issue_date=issue_date_obj,
                    status='draft'
                )
                
                # Create invoice items
                for item_data in cart_items:
                    item_type = item_data.get('type', 'service')
                    item_id = item_data.get('id')
                    quantity = int(item_data.get('quantity', 1))
                    price = float(item_data.get('price', 0))
                    name = item_data.get('name', '')
                    
                    # Create invoice item
                    invoice_item = InvoiceItem.objects.create(
                        invoice=invoice,
                        description=name,
                        quantity=quantity,
                        unit_price=price,
                        total_price=quantity * price,
                    )
                    
                    # Handle service
                    if item_type == 'service':
                        try:
                            service = Service.objects.get(pk=item_id)
                            invoice_item.service = service
                            invoice_item.save()
                        except Service.DoesNotExist:
                            pass
                    
                    # Handle inventory
                    elif item_type == 'inventory':
                        try:
                            inventory_item = InventoryItem.objects.get(pk=item_id)
                            invoice_item.inventory_item = inventory_item
                            invoice_item.save()
                            
                            # Update inventory
                            previous_quantity = inventory_item.quantity
                            inventory_item.quantity -= quantity
                            inventory_item.save()
                            
                            # Create stock movement
                            from inventory.models import StockMovement
                            StockMovement.objects.create(
                                item=inventory_item,
                                movement_type='sale',
                                quantity=-quantity,
                                previous_quantity=previous_quantity,
                                new_quantity=inventory_item.quantity,
                                reference_number=invoice.invoice_number,
                                notes=f"Used in invoice #{invoice.invoice_number}",
                                performed_by=request.user
                            )
                            print(f"Updated inventory for {inventory_item.name}: {previous_quantity} -> {inventory_item.quantity}")
                        except InventoryItem.DoesNotExist:
                            print(f"Inventory item not found: {item_id}")
                
                # Clear session cart
                request.session['cart_items'] = '[]'
            
            messages.success(request, f'Invoice {invoice.invoice_number} created successfully with {len(cart_items)} items!')
            return redirect('billing:detail', pk=invoice.pk)
            
        except Exception as e:
            messages.error(request, f'Error creating invoice: {str(e)}')
            import traceback
            print(traceback.format_exc())
            return redirect('billing:add')
    
    # GET request - initialize session cart
    from inventory.models import InventoryItem
    request.session['cart_items'] = '[]'
    patients = Patient.objects.filter(is_active=True).order_by('first_name', 'last_name')
    services = Service.objects.filter(is_active=True)
    inventory_items = InventoryItem.objects.filter(is_active=True, quantity__gt=0)
    
    return render(request, 'billing/invoice_add.html', {
        'patients': patients,
        'services': services,
        'inventory_items': inventory_items,
    })


@login_required
def invoice_detail(request, pk):
    """View invoice details"""
    invoice = get_object_or_404(Invoice, pk=pk)
    from inventory.models import InventoryItem
    inventory_items = InventoryItem.objects.filter(is_active=True, quantity__gt=0)
    return render(request, 'billing/invoice_detail.html', {
        'invoice': invoice,
        'inventory_items': inventory_items,
    })


@login_required
def add_payment(request, pk):
    """Add a payment to an invoice"""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    if request.method == 'POST':
        try:
            amount = float(request.POST.get('amount', 0))
            payment_method = request.POST.get('payment_method')
            payment_date = request.POST.get('payment_date', '')
            
            if amount <= 0:
                messages.error(request, 'Amount must be greater than 0')
                return redirect('billing:detail', pk=invoice.pk)
            
            if amount > invoice.balance_due:
                messages.error(request, f'Amount cannot exceed balance due: {invoice.balance_due}')
                return redirect('billing:detail', pk=invoice.pk)
            
            # Handle backdated payment date
            if payment_date:
                try:
                    from datetime import datetime
                    payment_datetime = datetime.strptime(payment_date, '%Y-%m-%d')
                    payment_date_obj = timezone.make_aware(payment_datetime)
                except:
                    payment_date_obj = timezone.now()
            else:
                payment_date_obj = timezone.now()
            
            Payment.objects.create(
                invoice=invoice,
                amount=amount,
                payment_method=payment_method,
                payment_date=payment_date_obj,
                status='completed'
            )
            
            # Update invoice status
            if invoice.balance_due <= 0:
                invoice.status = 'paid'
                invoice.payment_date = payment_date_obj
            else:
                invoice.status = 'partially_paid'
            invoice.save()
            
            messages.success(request, f'Payment of {amount} received successfully!')
        except Exception as e:
            messages.error(request, f'Error processing payment: {str(e)}')
    
    return redirect('billing:detail', pk=invoice.pk)


@login_required
def print_invoice(request, pk):
    """Print invoice view (PDF friendly)"""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Get company settings
    from core.models import CompanySettings
    company = CompanySettings.get_settings()
    
    return render(request, 'billing/invoice_print.html', {
        'invoice': invoice,
        'company': company,
    })


@login_required
def invoice_delete(request, pk):
    """Delete an invoice"""
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        invoice.delete()
        messages.success(request, 'Invoice deleted successfully!')
        return redirect('billing:list')
    return render(request, 'billing/invoice_delete.html', {'invoice': invoice})


@login_required
def invoice_add(request):
    """Add a new invoice with items from cart"""
    from inventory.models import InventoryItem
    from django.db import transaction
    import json
    from datetime import datetime
    
    if request.method == 'POST':
        try:
            # Debug: Print all POST data
            print("=" * 60)
            print("POST DATA RECEIVED:")
            for key, value in request.POST.items():
                print(f"  {key}: {value[:100] if len(str(value)) > 100 else value}")
            print("=" * 60)
            
            patient_id = request.POST.get('patient')
            cart_items_json = request.POST.get('cart_items', '[]')
            issue_date = request.POST.get('issue_date', '')
            
            # Try to get cart items from session if POST doesn't have it
            if not cart_items_json or cart_items_json == '[]':
                cart_items_json = request.session.get('cart_items', '[]')
                print(f"Using session cart data: {cart_items_json}")
            
            # Parse cart items
            try:
                cart_items = json.loads(cart_items_json)
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}")
                cart_items = []
            
            print(f"Parsed cart items: {cart_items}")
            print(f"Number of items: {len(cart_items)}")
            
            if not patient_id:
                messages.error(request, 'Please select a patient')
                return redirect('billing:add')
            
            if not cart_items or len(cart_items) == 0:
                messages.error(request, 'Please add at least one item to the invoice')
                return redirect('billing:add')
            
            patient = get_object_or_404(Patient, pk=patient_id)
            
            # Generate invoice number
            last_invoice = Invoice.objects.order_by('-id').first()
            if last_invoice:
                invoice_number = f"INV-{last_invoice.id + 1:05d}"
            else:
                invoice_number = "INV-00001"
            
            with transaction.atomic():
                # Calculate subtotal
                subtotal = 0
                for item in cart_items:
                    price = float(item.get('price', 0))
                    quantity = int(item.get('quantity', 1))
                    subtotal += price * quantity
                
                tax_rate = float(request.POST.get('tax_rate', 0))
                discount = float(request.POST.get('discount', 0))
                tax_amount = (subtotal * tax_rate) / 100 if tax_rate > 0 else 0
                total_amount = subtotal + tax_amount - discount
                
                # Handle backdated issue date
                if issue_date:
                    try:
                        # Parse the date string
                        issue_datetime = datetime.strptime(issue_date, '%Y-%m-%d')
                        # Make it timezone aware
                        issue_date_obj = timezone.make_aware(issue_datetime)
                    except:
                        issue_date_obj = timezone.now()
                else:
                    issue_date_obj = timezone.now()
                
                # Handle backdated due date
                due_date = request.POST.get('due_date', '')
                due_date_obj = None
                if due_date:
                    try:
                        due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
                    except:
                        pass
                
                # Create invoice
                invoice = Invoice.objects.create(
                    invoice_number=invoice_number,
                    patient=patient,
                    patient_name=patient.full_name,
                    patient_phone=patient.phone,
                    subtotal=subtotal,
                    tax_rate=tax_rate,
                    tax_amount=tax_amount,
                    discount=discount,
                    total_amount=total_amount,
                    amount_paid=0,
                    balance_due=total_amount,
                    notes=request.POST.get('notes', ''),
                    due_date=due_date_obj,
                    issue_date=issue_date_obj,
                    status='draft'
                )
                
                # Create invoice items
                for item_data in cart_items:
                    item_type = item_data.get('type', 'service')
                    item_id = item_data.get('id')
                    quantity = int(item_data.get('quantity', 1))
                    price = float(item_data.get('price', 0))
                    name = item_data.get('name', '')
                    
                    # Create invoice item
                    invoice_item = InvoiceItem.objects.create(
                        invoice=invoice,
                        description=name,
                        quantity=quantity,
                        unit_price=price,
                        total_price=quantity * price,
                    )
                    
                    # Handle service
                    if item_type == 'service':
                        try:
                            service = Service.objects.get(pk=item_id)
                            invoice_item.service = service
                            invoice_item.save()
                        except Service.DoesNotExist:
                            pass
                    
                    # Handle inventory
                    elif item_type == 'inventory':
                        try:
                            inventory_item = InventoryItem.objects.get(pk=item_id)
                            invoice_item.inventory_item = inventory_item
                            invoice_item.save()
                            
                            # Update inventory
                            previous_quantity = inventory_item.quantity
                            inventory_item.quantity -= quantity
                            inventory_item.save()
                            
                            # Create stock movement
                            from inventory.models import StockMovement
                            StockMovement.objects.create(
                                item=inventory_item,
                                movement_type='sale',
                                quantity=-quantity,
                                previous_quantity=previous_quantity,
                                new_quantity=inventory_item.quantity,
                                reference_number=invoice.invoice_number,
                                notes=f"Used in invoice #{invoice.invoice_number}",
                                performed_by=request.user
                            )
                            print(f"Updated inventory for {inventory_item.name}: {previous_quantity} -> {inventory_item.quantity}")
                        except InventoryItem.DoesNotExist:
                            print(f"Inventory item not found: {item_id}")
                
                # Clear session cart
                request.session['cart_items'] = '[]'
            
            messages.success(request, f'Invoice {invoice.invoice_number} created successfully with {len(cart_items)} items!')
            return redirect('billing:detail', pk=invoice.pk)
            
        except Exception as e:
            messages.error(request, f'Error creating invoice: {str(e)}')
            import traceback
            print(traceback.format_exc())
            return redirect('billing:add')
    
    # GET request - initialize session cart
    from inventory.models import InventoryItem
    request.session['cart_items'] = '[]'
    patients = Patient.objects.filter(is_active=True).order_by('first_name', 'last_name')
    services = Service.objects.filter(is_active=True)
    inventory_items = InventoryItem.objects.filter(is_active=True, quantity__gt=0)
    
    return render(request, 'billing/invoice_add.html', {
        'patients': patients,
        'services': services,
        'inventory_items': inventory_items,
    })

@login_required
def add_invoice_item(request, pk):
    """Add item to invoice (service or inventory)"""
    invoice = get_object_or_404(Invoice, pk=pk)
    from inventory.models import InventoryItem, StockMovement
    from django.db import transaction
    from django.db.models import Sum
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                item_type = request.POST.get('item_type', 'service')
                description = request.POST.get('description', '').strip()
                quantity_str = request.POST.get('quantity', '1')
                unit_price_str = request.POST.get('unit_price', '0')
                
                # Convert to numbers
                try:
                    quantity = int(quantity_str) if quantity_str else 1
                    if quantity < 1:
                        quantity = 1
                except (ValueError, TypeError):
                    quantity = 1
                    
                try:
                    unit_price = float(unit_price_str) if unit_price_str else 0.0
                    if unit_price < 0:
                        unit_price = 0.0
                except (ValueError, TypeError):
                    unit_price = 0.0
                
                if not description:
                    messages.error(request, 'Description is required')
                    return redirect('billing:detail', pk=invoice.pk)
                
                if unit_price <= 0:
                    messages.error(request, 'Unit price must be greater than 0')
                    return redirect('billing:detail', pk=invoice.pk)
                
                total_price = quantity * unit_price
                
                # Create the invoice item first
                invoice_item = InvoiceItem.objects.create(
                    invoice=invoice,
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=total_price,
                )
                
                # Handle service
                if item_type == 'service':
                    service_id = request.POST.get('service')
                    if service_id:
                        try:
                            service = Service.objects.get(pk=service_id)
                            invoice_item.service = service
                            invoice_item.save(update_fields=['service'])
                        except Service.DoesNotExist:
                            pass
                
                # Handle inventory item - update stock AFTER creating invoice item
                if item_type == 'inventory':
                    inventory_id = request.POST.get('inventory_item')
                    if inventory_id:
                        try:
                            inventory_item = InventoryItem.objects.get(pk=inventory_id)
                            
                            # Check if enough stock
                            if inventory_item.quantity < quantity:
                                messages.error(request, f'Not enough stock! Available: {inventory_item.quantity}')
                                # Delete the invoice item we just created
                                invoice_item.delete()
                                return redirect('billing:detail', pk=invoice.pk)
                            
                            # Link inventory item to invoice item
                            invoice_item.inventory_item = inventory_item
                            invoice_item.save(update_fields=['inventory_item'])
                            
                            # Update inventory quantity
                            previous_quantity = inventory_item.quantity
                            inventory_item.quantity -= quantity
                            inventory_item.save()
                            
                            # Create stock movement
                            StockMovement.objects.create(
                                item=inventory_item,
                                movement_type='sale',
                                quantity=-quantity,
                                previous_quantity=previous_quantity,
                                new_quantity=inventory_item.quantity,
                                reference_number=invoice.invoice_number,
                                notes=f"Used in invoice #{invoice.invoice_number}",
                                performed_by=request.user
                            )
                            
                            messages.success(request, f'Inventory updated: {inventory_item.quantity} remaining')
                            
                        except InventoryItem.DoesNotExist:
                            messages.warning(request, 'Inventory item not found')
                
                # Update invoice totals
                subtotal = invoice.items.aggregate(Sum('total_price'))['total_price__sum'] or 0
                invoice.subtotal = subtotal
                invoice.tax_amount = (subtotal * invoice.tax_rate) / 100 if invoice.tax_rate > 0 else 0
                invoice.total_amount = subtotal + invoice.tax_amount - invoice.discount
                invoice.balance_due = invoice.total_amount - invoice.amount_paid
                invoice.save()
                
                messages.success(request, 'Item added to invoice successfully!')
                
        except Exception as e:
            messages.error(request, f'Error adding item: {str(e)}')
            import traceback
            print(traceback.format_exc())
    
    return redirect('billing:detail', pk=invoice.pk)


@login_required
def remove_invoice_item(request, pk, item_pk):
    """Remove item from invoice"""
    item = get_object_or_404(InvoiceItem, pk=item_pk, invoice_id=pk)
    invoice = item.invoice
    
    try:
        item.delete()
        
        # Update invoice totals
        from django.db.models import Sum
        subtotal = invoice.items.aggregate(Sum('total_price'))['total_price__sum'] or 0
        invoice.subtotal = subtotal
        invoice.tax_amount = (subtotal * invoice.tax_rate) / 100 if invoice.tax_rate > 0 else 0
        invoice.total_amount = subtotal + invoice.tax_amount - invoice.discount
        invoice.balance_due = invoice.total_amount - invoice.amount_paid
        invoice.save()
        
        messages.success(request, 'Item removed from invoice!')
    except Exception as e:
        messages.error(request, f'Error removing item: {str(e)}')
    
    return redirect('billing:detail', pk=invoice.pk)


@login_required
def store_cart(request):
    """Store cart items in session via AJAX"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cart_items = data.get('cart_items', '[]')
            request.session['cart_items'] = cart_items
            return JsonResponse({'success': True, 'message': 'Cart stored in session'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


# ====================
# EXPENSE VIEWS
# ====================

@login_required
def expense_list(request):
    """List all expenses"""
    expenses = Expense.objects.all().order_by('-expense_date')
    
    # Filter by date range
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    if start_date:
        expenses = expenses.filter(expense_date__gte=start_date)
    if end_date:
        expenses = expenses.filter(expense_date__lte=end_date)
    
    # Filter by category
    category = request.GET.get('category', '')
    if category:
        expenses = expenses.filter(category=category)
    
    # Calculate totals
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'expenses': expenses,
        'total_expenses': total_expenses,
        'categories': Expense.EXPENSE_CATEGORIES,
        'start_date': start_date,
        'end_date': end_date,
        'category_filter': category,
    }
    return render(request, 'billing/expense_list.html', context)


@login_required
def expense_add(request):
    """Add a new expense"""
    if request.method == 'POST':
        try:
            expense = Expense.objects.create(
                description=request.POST.get('description'),
                category=request.POST.get('category'),
                amount=request.POST.get('amount'),
                expense_date=request.POST.get('expense_date') or timezone.now().date(),
                payment_method=request.POST.get('payment_method', 'cash'),
                reference_number=request.POST.get('reference_number', ''),
                notes=request.POST.get('notes', ''),
                created_by=request.user
            )
            
            # Handle receipt upload
            if request.FILES.get('receipt'):
                expense.receipt = request.FILES.get('receipt')
                expense.save()
            
            messages.success(request, 'Expense added successfully!')
            return redirect('billing:expense_list')
        except Exception as e:
            messages.error(request, f'Error adding expense: {str(e)}')
    
    return render(request, 'billing/expense_add.html', {
        'categories': Expense.EXPENSE_CATEGORIES,
        'payment_methods': Expense.PAYMENT_METHOD_CHOICES,
    })


@login_required
def expense_edit(request, pk):
    """Edit an expense"""
    expense = get_object_or_404(Expense, pk=pk)
    
    if request.method == 'POST':
        try:
            expense.description = request.POST.get('description')
            expense.category = request.POST.get('category')
            expense.amount = request.POST.get('amount')
            expense.expense_date = request.POST.get('expense_date')
            expense.payment_method = request.POST.get('payment_method', 'cash')
            expense.reference_number = request.POST.get('reference_number', '')
            expense.notes = request.POST.get('notes', '')
            
            if request.FILES.get('receipt'):
                if expense.receipt:
                    expense.receipt.delete()
                expense.receipt = request.FILES.get('receipt')
            
            expense.save()
            messages.success(request, 'Expense updated successfully!')
            return redirect('billing:expense_list')
        except Exception as e:
            messages.error(request, f'Error updating expense: {str(e)}')
    
    return render(request, 'billing/expense_edit.html', {
        'expense': expense,
        'categories': Expense.EXPENSE_CATEGORIES,
        'payment_methods': Expense.PAYMENT_METHOD_CHOICES,
    })


@login_required
def expense_delete(request, pk):
    """Delete an expense"""
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        if expense.receipt:
            expense.receipt.delete()
        expense.delete()
        messages.success(request, 'Expense deleted successfully!')
        return redirect('billing:expense_list')
    
    return render(request, 'billing/expense_delete.html', {'expense': expense})


# ====================
# BALANCE SHEET
# ====================

@login_required
def balance_sheet(request):
    """Generate balance sheet report"""
    from django.db.models import Sum
    from datetime import datetime, date
    
    # Get date range from request
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    
    # Default to current month
    today = date.today()
    if not start_date_str and not end_date_str:
        start_date = today.replace(day=1)
        end_date = today
    else:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else today.replace(day=1)
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else today
        except ValueError:
            start_date = today.replace(day=1)
            end_date = today
    
    # ✅ FIXED: Removed __date lookup since issue_date is DateField
    invoices = Invoice.objects.all()
    expenses = Expense.objects.all()
    
    if start_date:
        invoices = invoices.filter(issue_date__gte=start_date)  # ✅ Fixed
        expenses = expenses.filter(expense_date__gte=start_date)
    if end_date:
        invoices = invoices.filter(issue_date__lte=end_date)  # ✅ Fixed
        expenses = expenses.filter(expense_date__lte=end_date)
    
    # Revenue calculations
    total_invoices = invoices.count()
    total_revenue = invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    paid_amount = invoices.filter(status='paid').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    pending_amount = invoices.filter(status__in=['draft', 'sent', 'partially_paid']).aggregate(Sum('balance_due'))['balance_due__sum'] or 0
    
    # Expense calculations
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    expenses_by_category = expenses.values('category').annotate(total=Sum('amount')).order_by('-total')
    
    # Net profit
    net_profit = total_revenue - total_expenses
    
    # Revenue by payment method
    revenue_by_method = invoices.filter(status='paid').values('payment_method').annotate(
        total=Sum('total_amount')
    ).order_by('-total')
    
    # Format dates for display
    start_date_display = start_date.strftime('%b %d, %Y')
    end_date_display = end_date.strftime('%b %d, %Y')
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'start_date_display': start_date_display,
        'end_date_display': end_date_display,
        'start_date_str': start_date.strftime('%Y-%m-%d'),
        'end_date_str': end_date.strftime('%Y-%m-%d'),
        'total_invoices': total_invoices,
        'total_revenue': total_revenue,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'expenses_by_category': expenses_by_category,
        'revenue_by_method': revenue_by_method,
        'paid_invoices': Invoice.objects.filter(status='paid').count(),  # Add this
        'pending_invoices': Invoice.objects.filter(status__in=['draft', 'sent', 'partially_paid']).count(),  # Add this
    }
    return render(request, 'billing/balance_sheet.html', context)