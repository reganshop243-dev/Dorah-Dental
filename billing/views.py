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
from functools import wraps
from core.permissions import is_financial_staff


def financial_only(permission_code=None):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not is_financial_staff(request.user):
                messages.error(request, "Financial and billing access is restricted to administrators and accountants.")
                return redirect("core:dashboard")
            if permission_code and not request.user.profile.has_permission(permission_code):
                messages.error(request, "You do not have permission to perform this financial action.")
                return redirect("core:dashboard")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator



def is_doctor(user):
    """Return True when the authenticated user is a doctor."""
    return (
        user.is_authenticated
        and hasattr(user, 'profile')
        and user.profile.has_role('doctor')
        and not user.profile.has_any_role(['admin', 'accountant'])
    )


def is_admin(user):
    """Return True when the authenticated user is an administrator."""
    return (
        user.is_authenticated
        and hasattr(user, 'profile')
        and user.profile.has_role('admin')
    )

@login_required
def invoice_list(request):
    """List invoices with payment-aware Today / This Month / All filters."""
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.db.models import Q, Sum, Value, DecimalField, Exists, OuterRef
    from django.db.models.functions import Coalesce

    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    payment_method_filter = request.GET.get('payment_method', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    period = request.GET.get('period', 'today').strip().lower()
    if period not in ('today', 'this_month', 'all', 'custom'):
        period = 'today'

    today = timezone.localdate()
    start_of_month = today.replace(day=1)

    invoices = Invoice.objects.all()

    # Calculate paid strictly from completed Payment rows.
    # IMPORTANT: use EXISTS for activity/payment-method filters below instead
    # of joining payments again. Multiple joins to the same one-to-many
    # relation can multiply SUM(payments__amount), e.g. 250k + 50k becoming
    # 600k when the invoice also has a matching activity row.
    invoices = invoices.annotate(
        actual_paid=Coalesce(
            Sum('payments__amount', filter=Q(payments__status='completed')),
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )

    completed_payments = Payment.objects.filter(
        invoice=OuterRef('pk'),
        status='completed',
    )

    if search_query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search_query) |
            Q(patient_name__icontains=search_query) |
            Q(patient_phone__icontains=search_query) |
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query)
        )

    if status_filter:
        invoices = invoices.filter(status=status_filter)

    if payment_method_filter:
        invoices = invoices.filter(
            Q(payment_method=payment_method_filter) |
            Exists(completed_payments.filter(payment_method=payment_method_filter))
        )

    # Quick date views are based on invoice activity: an invoice appears if it
    # was issued in the period OR received a completed payment in the period.
    # EXISTS prevents the activity test from multiplying the payment SUM.
    if date_from or date_to:
        period = 'custom'
        payment_activity = completed_payments
        if date_from and date_to:
            payment_activity = payment_activity.filter(
                payment_date__gte=date_from, payment_date__lte=date_to
            )
            invoices = invoices.filter(
                Q(issue_date__gte=date_from, issue_date__lte=date_to) |
                Exists(payment_activity)
            )
        elif date_from:
            payment_activity = payment_activity.filter(payment_date__gte=date_from)
            invoices = invoices.filter(
                Q(issue_date__gte=date_from) | Exists(payment_activity)
            )
        elif date_to:
            payment_activity = payment_activity.filter(payment_date__lte=date_to)
            invoices = invoices.filter(
                Q(issue_date__lte=date_to) | Exists(payment_activity)
            )
    elif period == 'today':
        payment_activity = completed_payments.filter(payment_date=today)
        invoices = invoices.filter(
            Q(issue_date=today) | Exists(payment_activity)
        )
    elif period == 'this_month':
        payment_activity = completed_payments.filter(
            payment_date__gte=start_of_month, payment_date__lte=today
        )
        invoices = invoices.filter(
            Q(issue_date__gte=start_of_month, issue_date__lte=today) |
            Exists(payment_activity)
        )
    # period == all: no date restriction

    invoices = invoices.distinct().order_by('-issue_date', '-id')

    paginator = Paginator(invoices, 20)
    page = request.GET.get('page', 1)
    try:
        invoices_page = paginator.page(page)
    except PageNotAnInteger:
        invoices_page = paginator.page(1)
    except EmptyPage:
        invoices_page = paginator.page(paginator.num_pages)

    # Expose the effective balance and latest payment information to the list.
    for invoice in invoices_page.object_list:
        invoice.actual_balance = max(
            invoice.total_amount - invoice.actual_paid,
            0
        )
        invoice.latest_payment = invoice.payments.filter(
            status='completed'
        ).order_by('-payment_date', '-id').first()

    context = {
        'invoices': invoices_page,
        'paginator': paginator,
        'page_obj': invoices_page,
        'is_paginated': invoices_page.has_other_pages(),
        'total_count': paginator.count,
        'search_query': search_query,
        'status_filter': status_filter,
        'payment_method_filter': payment_method_filter,
        'date_from': date_from,
        'date_to': date_to,
        'period': period,
        'status_choices': Invoice.STATUS_CHOICES,
        'payment_method_choices': Invoice.PAYMENT_METHOD_CHOICES,
    }
    return render(request, 'billing/invoice_list.html', context)


@login_required
@financial_only("billing.create")
def invoice_add(request):
    """Add a new invoice with items from cart"""

    if is_doctor(request.user):
        messages.error(
            request,
            '❌ Doctors are not allowed to create invoices.'
        )
        return redirect('patients:list')

    from inventory.models import InventoryItem
    from django.db import transaction

    if request.method == 'POST':
        try:
            # Debug: Print all POST data
            print("=" * 60)
            print("POST DATA RECEIVED:")

            for key, value in request.POST.items():
                print(
                    f"  {key}: "
                    f"{value[:100] if len(str(value)) > 100 else value}"
                )

            print("=" * 60)

            patient_id = request.POST.get('patient')

            # IMPORTANT:
            # Get invoice type from the form.
            # Default to normal invoice if nothing is submitted.
            invoice_type = request.POST.get(
                'invoice_type',
                'invoice'
            )

            # Only allow the two valid invoice types.
            if invoice_type not in ('invoice', 'booking'):
                invoice_type = 'invoice'

            cart_items_json = request.POST.get(
                'cart_items',
                '[]'
            )

            issue_date = request.POST.get(
                'issue_date',
                ''
            )

            # Try to get cart items from session if POST doesn't have them
            if not cart_items_json or cart_items_json == '[]':
                cart_items_json = request.session.get(
                    'cart_items',
                    '[]'
                )

                print(
                    f"Using session cart data: {cart_items_json}"
                )

            # Parse cart items
            try:
                cart_items = json.loads(cart_items_json)
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}")
                cart_items = []

            print(f"Parsed cart items: {cart_items}")
            print(f"Number of items: {len(cart_items)}")

            # Validate patient
            if not patient_id:
                messages.error(
                    request,
                    'Please select a patient'
                )
                return redirect('billing:add')

            # Validate cart
            if not cart_items:
                messages.error(
                    request,
                    'Please add at least one item to the invoice'
                )
                return redirect('billing:add')

            patient = get_object_or_404(
                Patient,
                pk=patient_id
            )

            # Generate invoice number
            last_invoice = Invoice.objects.order_by('-id').first()

            if last_invoice:
                invoice_number = (
                    f"INV-{last_invoice.id + 1:05d}"
                )
            else:
                invoice_number = "INV-00001"

            with transaction.atomic():

                # -----------------------------------------
                # CALCULATE TOTALS
                # -----------------------------------------

                subtotal = 0

                for item in cart_items:
                    price = float(
                        item.get('price', 0)
                    )

                    quantity = int(
                        item.get('quantity', 1)
                    )

                    subtotal += price * quantity

                tax_rate = float(
                    request.POST.get(
                        'tax_rate',
                        0
                    )
                )

                discount = float(
                    request.POST.get(
                        'discount',
                        0
                    )
                )

                tax_amount = (
                    subtotal * tax_rate
                ) / 100 if tax_rate > 0 else 0

                total_amount = (
                    subtotal
                    + tax_amount
                    - discount
                )

                # -----------------------------------------
                # ISSUE DATE
                # -----------------------------------------

                if issue_date:
                    try:
                        from datetime import datetime

                        issue_datetime = datetime.strptime(
                            issue_date,
                            '%Y-%m-%d'
                        )

                        issue_date_obj = timezone.make_aware(
                            issue_datetime
                        )

                    except (ValueError, TypeError):
                        issue_date_obj = timezone.now()

                else:
                    issue_date_obj = timezone.now()

                # -----------------------------------------
                # INITIAL PAYMENT
                # -----------------------------------------

                from decimal import Decimal, InvalidOperation

                initial_payment_raw = (
                    request.POST.get(
                        'initial_payment'
                    ) or '0'
                ).strip()

                try:
                    initial_payment = Decimal(
                        initial_payment_raw
                    )

                except (
                    InvalidOperation,
                    ValueError
                ):
                    initial_payment = Decimal('0')

                # Payment cannot be negative
                # and cannot exceed invoice total.
                if (
                    initial_payment < 0
                    or initial_payment > Decimal(
                        str(total_amount)
                    )
                ):
                    raise ValueError(
                        'Initial payment cannot be negative '
                        'or greater than the invoice total.'
                    )

                initial_payment_method = (
                    request.POST.get(
                        'initial_payment_method',
                        ''
                    ).strip()
                )

                initial_payment_date_raw = (
                    request.POST.get(
                        'initial_payment_date',
                        ''
                    ).strip()
                )

                initial_payment_date = None

                if initial_payment > 0:

                    from datetime import datetime

                    if initial_payment_date_raw:
                        try:
                            initial_payment_date = (
                                datetime.strptime(
                                    initial_payment_date_raw,
                                    '%Y-%m-%d'
                                ).date()
                            )

                        except ValueError:
                            initial_payment_date = (
                                timezone.localdate()
                            )

                    else:
                        initial_payment_date = (
                            timezone.localdate()
                        )

                    if not initial_payment_method:
                        raise ValueError(
                            'Please select a payment method '
                            'for the initial payment.'
                        )

                # -----------------------------------------
                # CREATE INVOICE
                # -----------------------------------------

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
                    notes=request.POST.get(
                        'notes',
                        ''
                    ),
                    due_date=request.POST.get(
                        'due_date'
                    ) or None,
                    issue_date=issue_date_obj,

                    # Booking / normal invoice
                    invoice_type=invoice_type,

                    # Booking must remain BOOKED
                    status=(
                        'booked'
                        if invoice_type == 'booking'
                        else 'draft'
                    )
                )

                # -----------------------------------------
                # RECORD INITIAL PAYMENT
                # -----------------------------------------

                # This creates a REAL payment transaction.
                # Therefore money paid today appears in
                # today's collections/income.

                if initial_payment > 0:

                    Payment.objects.create(
                        invoice=invoice,
                        amount=initial_payment,
                        payment_date=initial_payment_date,
                        payment_method=initial_payment_method,
                        status='completed',
                        processed_by=request.user.get_username(),
                        notes=(
                            'Initial payment recorded when '
                            'invoice/booking was created.'
                        )
                    )

                # -----------------------------------------
                # CREATE INVOICE ITEMS
                # -----------------------------------------

                for item_data in cart_items:

                    item_type = item_data.get(
                        'type',
                        'service'
                    )

                    item_id = item_data.get('id')

                    quantity = int(
                        item_data.get(
                            'quantity',
                            1
                        )
                    )

                    price = float(
                        item_data.get(
                            'price',
                            0
                        )
                    )

                    name = item_data.get(
                        'name',
                        ''
                    )

                    # Create invoice item
                    invoice_item = InvoiceItem.objects.create(
                        invoice=invoice,
                        description=name,
                        quantity=quantity,
                        unit_price=price,
                        total_price=quantity * price,
                    )

                    # -------------------------------------
                    # SERVICE
                    # -------------------------------------

                    if item_type == 'service':

                        try:
                            service = Service.objects.get(
                                pk=item_id
                            )

                            invoice_item.service = service
                            invoice_item.save()

                        except Service.DoesNotExist:
                            pass

                    # -------------------------------------
                    # INVENTORY ITEM
                    # -------------------------------------

                    elif item_type == 'inventory':

                        try:
                            inventory_item = (
                                InventoryItem.objects.get(
                                    pk=item_id
                                )
                            )

                            invoice_item.inventory_item = (
                                inventory_item
                            )

                            invoice_item.save()

                            # Update inventory
                            previous_quantity = (
                                inventory_item.quantity
                            )

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
                                reference_number=(
                                    invoice.invoice_number
                                ),
                                notes=(
                                    f"Used in invoice "
                                    f"#{invoice.invoice_number}"
                                ),
                                performed_by=request.user
                            )

                            print(
                                f"Updated inventory for "
                                f"{inventory_item.name}: "
                                f"{previous_quantity} -> "
                                f"{inventory_item.quantity}"
                            )

                        except InventoryItem.DoesNotExist:
                            print(
                                f"Inventory item not found: "
                                f"{item_id}"
                            )

                # -----------------------------------------
                # CLEAR SESSION CART
                # -----------------------------------------

                request.session['cart_items'] = '[]'

            # ---------------------------------------------
            # SUCCESS
            # ---------------------------------------------

            messages.success(
                request,
                f'Invoice {invoice.invoice_number} '
                f'created successfully with '
                f'{len(cart_items)} items!'
            )

            return redirect(
                'billing:detail',
                pk=invoice.pk
            )

        except Exception as e:

            messages.error(
                request,
                'Sorry, we could not complete that request. '
                'Please try again. If the problem continues, '
                'contact the administrator.'
            )

            import traceback
            print(traceback.format_exc())

            return redirect('billing:add')

    # =============================================
    # GET REQUEST
    # =============================================

    from inventory.models import InventoryItem

    request.session['cart_items'] = '[]'

    patients = Patient.objects.filter(
        is_active=True
    ).order_by(
        'first_name',
        'last_name'
    )

    services = Service.objects.filter(
        is_active=True
    )

    inventory_items = InventoryItem.objects.filter(
        is_active=True,
        quantity__gt=0
    )

    # Preserve a patient selected before opening
    # the invoice form.
    selected_patient = None
    selected_patient_balance = 0

    selected_patient_id = request.GET.get(
        'patient'
    )

    if selected_patient_id:

        try:
            selected_patient = Patient.objects.get(
                pk=selected_patient_id,
                is_active=True
            )

            from billing.balance_service import (
                get_patient_outstanding_balance
            )

            selected_patient_balance = (
                get_patient_outstanding_balance(
                    selected_patient
                )
            )

        except (
            Patient.DoesNotExist,
            ValueError,
            TypeError
        ):
            selected_patient = None

    return render(
        request,
        'billing/invoice_add.html',
        {
            'patients': patients,
            'services': services,
            'inventory_items': inventory_items,
            'selected_patient': selected_patient,
            'selected_patient_balance': selected_patient_balance,
        }
    )



@login_required
@financial_only("billing.edit")
def invoice_edit(request, pk):
    """Edit invoice header/financial fields and existing line items safely."""
    if is_doctor(request.user):
        messages.error(request, 'Doctors are not allowed to modify invoices.')
        return redirect('billing:detail', pk=pk)

    from decimal import Decimal, InvalidOperation
    from django.db import transaction

    invoice = get_object_or_404(Invoice, pk=pk)
    items = list(invoice.items.select_related('service', 'inventory_item').all())

    if request.method == 'POST':
        try:
            with transaction.atomic():
                issue_date = request.POST.get('issue_date') or invoice.issue_date
                due_date = request.POST.get('due_date') or None
                invoice_type = request.POST.get('invoice_type', invoice.invoice_type)
                if invoice_type not in dict(Invoice.INVOICE_TYPE_CHOICES):
                    raise ValueError('Invalid invoice type.')

                def dec(name, default='0'):
                    raw = (request.POST.get(name, default) or default).strip()
                    value = Decimal(raw)
                    if value < 0:
                        raise ValueError(f'{name} cannot be negative')
                    return value

                tax_rate = dec('tax_rate')
                discount = dec('discount')
                invoice.issue_date = issue_date
                invoice.due_date = due_date
                invoice.tax_rate = tax_rate
                invoice.discount = discount
                invoice.notes = request.POST.get('notes', '').strip()
                invoice.invoice_type = invoice_type
                if invoice.invoice_type == 'booking' and invoice.status != 'cancelled':
                    invoice.status = 'booked'

                for item in items:
                    prefix = f'item_{item.pk}_'
                    description = request.POST.get(prefix + 'description')
                    quantity_raw = request.POST.get(prefix + 'quantity')
                    unit_price_raw = request.POST.get(prefix + 'unit_price')
                    if description is None:
                        continue

                    quantity = int(quantity_raw or item.quantity)
                    unit_price = Decimal(unit_price_raw or item.unit_price)
                    if quantity < 1:
                        raise ValueError(f'Quantity for "{item.description}" must be at least 1')
                    if unit_price < 0:
                        raise ValueError(f'Price for "{item.description}" cannot be negative')

                    # Inventory-linked quantities cannot be changed here because
                    # doing so without a stock movement would corrupt stock.
                    if item.inventory_item:
                        quantity = item.quantity

                    item.description = description.strip() or item.description
                    item.quantity = quantity
                    item.unit_price = unit_price
                    item.total_price = unit_price * quantity
                    item.save(update_fields=['description', 'quantity', 'unit_price', 'total_price'])

                subtotal = sum((item.total_price for item in invoice.items.all()), Decimal('0.00'))
                tax_amount = (subtotal * tax_rate) / Decimal('100')
                total_amount = subtotal + tax_amount - discount
                if total_amount < 0:
                    raise ValueError('Discount cannot be greater than the invoice subtotal plus tax.')

                invoice.subtotal = subtotal
                invoice.tax_amount = tax_amount
                invoice.total_amount = total_amount
                invoice.save(update_fields=[
                    'issue_date', 'due_date', 'tax_rate', 'discount', 'notes',
                    'invoice_type', 'status', 'subtotal', 'tax_amount', 'total_amount', 'updated_at'
                ])

                invoice.sync_payment_state()
                invoice.save(update_fields=[
                    'amount_paid', 'balance_due', 'status', 'payment_date', 'updated_at'
                ])

            messages.success(request, f'Invoice {invoice.invoice_number} updated successfully.')
            return redirect('billing:detail', pk=invoice.pk)

        except (ValueError, InvalidOperation) as e:
            messages.error(request, str(e))
        except Exception:
            messages.error(request, 'We could not update this invoice. No changes were saved.')

    invoice.refresh_from_db()
    items = invoice.items.select_related('service', 'inventory_item').all()
    return render(request, 'billing/invoice_edit.html', {
        'invoice': invoice,
        'items': items,
        'is_doctor': is_doctor(request.user),
    })


@login_required
@financial_only("billing.view")
def invoice_detail(request, pk):
    """View invoice details with role-based financial protection."""
    invoice = get_object_or_404(Invoice, pk=pk)
    from inventory.models import InventoryItem
    inventory_items = InventoryItem.objects.filter(is_active=True, quantity__gt=0)
    return render(request, 'billing/invoice_detail.html', {
        'invoice': invoice,
        'inventory_items': inventory_items,
        'is_doctor': is_doctor(request.user),
    })


@login_required
@financial_only("billing.payments.create")
def add_payment(request, pk):
    """Add a payment to an invoice"""
    if is_doctor(request.user):
        messages.error(request, '❌ Doctors are not allowed to access invoice payments.')
        return redirect('billing:detail', pk=pk)
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
            
            # Payment.save() recalculates all completed installments and
            # synchronizes the invoice to paid/partially_paid automatically.
            invoice.refresh_from_db()
            
            messages.success(request, f'Payment of {amount} received successfully!')
        except Exception as e:
            messages.error(request, 'Sorry, we could not complete that request. Please try again. If the problem continues, contact the administrator.')
    
    return redirect('billing:detail', pk=invoice.pk)


@login_required
@financial_only("billing.print")
def print_invoice(request, pk):
    """Print invoice view (PDF friendly)"""
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Get company settings
    from core.models import CompanySettings
    company = CompanySettings.get_settings()
    
    return render(request, 'billing/invoice_print.html', {
        'invoice': invoice,
        'company': company,
        'is_doctor': is_doctor(request.user),
    })


@login_required
@financial_only("billing.delete")
def invoice_delete(request, pk):
    """Delete an invoice"""
    if is_doctor(request.user):
        messages.error(request, '❌ Doctors are not allowed to delete invoices.')
        return redirect('billing:detail', pk=pk)
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        invoice.delete()
        messages.success(request, 'Invoice deleted successfully!')
        return redirect('billing:list')
    return render(request, 'billing/invoice_delete.html', {'invoice': invoice})




@login_required
@financial_only("billing.edit")
def add_invoice_item(request, pk):
    """Add item to invoice (service or inventory)"""
    if is_doctor(request.user):
        messages.error(request, '❌ Doctors are not allowed to modify invoices.')
        return redirect('billing:detail', pk=pk)
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
            messages.error(request, 'Sorry, we could not complete that request. Please try again. If the problem continues, contact the administrator.')
            import traceback
            print(traceback.format_exc())
    
    return redirect('billing:detail', pk=invoice.pk)


@login_required
@financial_only("billing.edit")
def remove_invoice_item(request, pk, item_pk):
    """Remove item from invoice"""
    if is_doctor(request.user):
        messages.error(request, '❌ Doctors are not allowed to modify invoices.')
        return redirect('billing:detail', pk=pk)
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
        messages.error(request, 'Sorry, we could not complete that request. Please try again. If the problem continues, contact the administrator.')
    
    return redirect('billing:detail', pk=invoice.pk)


@login_required
@financial_only("billing.view")
def store_cart(request):
    """Store cart items in session via AJAX"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cart_items = data.get('cart_items', '[]')
            request.session['cart_items'] = cart_items
            return JsonResponse({'success': True, 'message': 'Cart stored in session'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': 'Something went wrong. Please try again.', 'error_code': 'DD-API-500'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


# ====================
# EXPENSE VIEWS
# ====================

@login_required
@financial_only("billing.expenses.view")
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
@financial_only("billing.expenses.create")
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
            messages.error(request, 'Sorry, we could not complete that request. Please try again. If the problem continues, contact the administrator.')
    
    return render(request, 'billing/expense_add.html', {
        'categories': Expense.EXPENSE_CATEGORIES,
        'payment_methods': Expense.PAYMENT_METHOD_CHOICES,
    })


@login_required
@financial_only("billing.expenses.edit")
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
            messages.error(request, 'Sorry, we could not complete that request. Please try again. If the problem continues, contact the administrator.')
    
    return render(request, 'billing/expense_edit.html', {
        'expense': expense,
        'categories': Expense.EXPENSE_CATEGORIES,
        'payment_methods': Expense.PAYMENT_METHOD_CHOICES,
    })


@login_required
@financial_only("billing.expenses.delete")
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
@financial_only("reports.balance_sheet")
def balance_sheet(request):
    """Generate balance sheet report"""
    if is_doctor(request.user):
        messages.error(request, '❌ Doctors do not have access to financial reports.')
        return redirect('core:doctor_dashboard')
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
    paid_amount = Payment.objects.filter(
        status='completed',
        payment_date__gte=start_date,
        payment_date__lte=end_date,
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    pending_amount = invoices.filter(balance_due__gt=0, status__in=['draft', 'sent', 'partially_paid']).aggregate(Sum('balance_due'))['balance_due__sum'] or 0
    
    # Expense calculations
    total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0
    expenses_by_category = expenses.values('category').annotate(total=Sum('amount')).order_by('-total')
    
    # Net profit
    net_profit = total_revenue - total_expenses
    
    # Revenue by payment method
    revenue_by_method = Payment.objects.filter(
        status='completed',
        payment_date__gte=start_date,
        payment_date__lte=end_date,
    ).values('payment_method').annotate(
        total=Sum('amount')
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
        'pending_invoices': Invoice.objects.filter(balance_due__gt=0, status__in=['draft', 'sent', 'partially_paid']).count(),  # Add this
    }
    return render(request, 'billing/balance_sheet.html', context)
