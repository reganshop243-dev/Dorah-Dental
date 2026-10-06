from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, Q
from datetime import date, timedelta, datetime
from billing.models import Invoice
from appointments.models import Appointment, Doctor
from patients.models import Patient
from django.utils import timezone
from core.permissions import is_financial_staff

def financial_only(permission_code=None):
    def decorator(view_func):
        from functools import wraps
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not is_financial_staff(request.user):
                from django.contrib import messages
                from django.shortcuts import redirect
                messages.error(request, "Reports are restricted to administrators and accountants.")
                return redirect("core:dashboard")
            if permission_code and not request.user.profile.has_permission(permission_code):
                from django.contrib import messages
                from django.shortcuts import redirect
                messages.error(request, "You do not have permission to view this report.")
                return redirect("core:dashboard")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


@login_required
@financial_only("reports.aging")
def aging_report(request):
    """Accounts Receivable Aging Report based on actual completed payments."""
    from django.db.models import Sum, Q, Value, DecimalField
    from django.db.models.functions import Coalesce
    from decimal import Decimal

    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')

    end_date = date.today()
    start_date = end_date - timedelta(days=365)

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    invoices = Invoice.objects.filter(
        issue_date__lte=end_date
    ).exclude(status='cancelled').annotate(
        actual_paid=Coalesce(
            Sum('payments__amount', filter=Q(payments__status='completed')),
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )

    aging_data = {
        'zero_thirty': Decimal('0.00'),
        'thirty_sixty': Decimal('0.00'),
        'sixty_ninety': Decimal('0.00'),
        'over_90': Decimal('0.00'),
        'zero_thirty_count': 0,
        'thirty_sixty_count': 0,
        'sixty_ninety_count': 0,
        'over_90_count': 0,
        'invoices': [],
        'total_outstanding': Decimal('0.00'),
        'total_amount': Decimal('0.00'),
        'total_paid': Decimal('0.00'),
        'invoices_count': 0,
    }

    for invoice in invoices:
        total = Decimal(invoice.total_amount or 0)
        paid = Decimal(invoice.actual_paid or 0)
        balance = max(total - paid, Decimal('0.00'))

        if not invoice.issue_date or balance <= 0:
            continue

        age_days = max((end_date - invoice.issue_date).days, 0)
        invoice.age_days = age_days
        invoice.actual_paid = paid
        invoice.actual_balance = balance
        invoice.patient_name = invoice.patient_name or (invoice.patient.full_name if invoice.patient_id else 'Unknown')
        invoice.patient_phone = invoice.patient_phone or (invoice.patient.phone if invoice.patient_id else '')

        aging_data['invoices'].append(invoice)
        aging_data['total_amount'] += total
        aging_data['total_paid'] += paid
        aging_data['total_outstanding'] += balance
        aging_data['invoices_count'] += 1

        if age_days <= 30:
            aging_data['zero_thirty'] += balance
            aging_data['zero_thirty_count'] += 1
        elif age_days <= 60:
            aging_data['thirty_sixty'] += balance
            aging_data['thirty_sixty_count'] += 1
        elif age_days <= 90:
            aging_data['sixty_ninety'] += balance
            aging_data['sixty_ninety_count'] += 1
        else:
            aging_data['over_90'] += balance
            aging_data['over_90_count'] += 1

    return render(request, 'reports/aging.html', {
        'aging_data': aging_data,
        'start_date': start_date,
        'end_date': end_date,
        'start_date_str': start_date.strftime('%Y-%m-%d'),
        'end_date_str': end_date.strftime('%Y-%m-%d'),
        'start_date_display': start_date.strftime('%b %d, %Y'),
        'end_date_display': end_date.strftime('%b %d, %Y'),
    })


@login_required
@financial_only("reports.patient")
def patient_visits_report(request):
    """Patient Visit Report with actual completed payments for spending."""
    from django.db.models import Sum, Count, Q
    from decimal import Decimal

    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')

    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    appointments = Appointment.objects.filter(
        appointment_date__gte=start_date,
        appointment_date__lte=end_date,
        status='completed'
    )

    patient_ids = appointments.values_list('patient_id', flat=True).distinct()
    patients = Patient.objects.filter(id__in=patient_ids, is_active=True)

    patient_data = []
    total_patients = patients.count()
    total_visits = appointments.count()
    new_patients = 0
    returning_patients = 0

    for patient in patients:
        patient_appointments = appointments.filter(patient=patient)
        visit_count = patient_appointments.count()

        first_visit = patient_appointments.order_by('appointment_date').first()
        last_visit = patient_appointments.order_by('-appointment_date').first()

        previous_visits = Appointment.objects.filter(
            patient=patient,
            appointment_date__lt=start_date
        ).exists()

        if not previous_visits and visit_count > 0:
            new_patients += 1
        else:
            returning_patients += 1

        period_invoices = Invoice.objects.filter(
            patient=patient,
            issue_date__gte=start_date,
            issue_date__lte=end_date,
        )
        total_billed = period_invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        total_spent = Payment.objects.filter(
            invoice__in=period_invoices,
            status='completed',
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

        patient_data.append({
            'id': patient.id,
            'full_name': patient.full_name,
            'phone': patient.phone,
            'gender': patient.gender,
            'visit_count': visit_count,
            'total_billed': total_billed,
            'total_spent': total_spent,
            'avg_per_visit': total_spent / visit_count if visit_count > 0 else 0,
            'first_visit': first_visit.appointment_date if first_visit else None,
            'last_visit': last_visit.appointment_date if last_visit else None,
        })

    patient_data.sort(key=lambda x: x['total_spent'], reverse=True)

    context = {
        'patients': patient_data,
        'total_patients': total_patients,
        'total_visits': total_visits,
        'new_patients': new_patients,
        'returning_patients': returning_patients,
        'start_date': start_date,
        'end_date': end_date,
        'start_date_str': start_date.strftime('%Y-%m-%d'),
        'end_date_str': end_date.strftime('%Y-%m-%d'),
        'start_date_display': start_date.strftime('%b %d, %Y'),
        'end_date_display': end_date.strftime('%b %d, %Y'),
    }
    return render(request, 'reports/patient_visits.html', context)


@login_required
@financial_only("reports.doctor_performance")
def doctor_performance_report(request):
    """Doctor Performance Report using actual completed collections."""
    from django.db.models import Sum
    from decimal import Decimal

    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')

    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    doctors = Doctor.objects.filter(is_active=True)

    doctor_data = []
    total_revenue = Decimal('0.00')
    total_appointments = 0
    total_patients = 0

    for doctor in doctors:
        appointments = Appointment.objects.filter(
            doctor=doctor,
            appointment_date__gte=start_date,
            appointment_date__lte=end_date,
            status='completed'
        )

        appointment_count = appointments.count()
        patient_count = appointments.values('patient').distinct().count()

        # Collections are actual completed payments. The invoice's
        # appointment links the collection to the doctor responsible for it.
        revenue = Payment.objects.filter(
            invoice__appointment__in=appointments,
            status='completed',
            payment_date__gte=start_date,
            payment_date__lte=end_date,
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

        total_revenue += revenue
        total_appointments += appointment_count
        total_patients += patient_count

        doctor_data.append({
            'id': doctor.id,
            'name': doctor.name,
            'specialization': doctor.specialization,
            'appointment_count': appointment_count,
            'patient_count': patient_count,
            'total_revenue': revenue,
            'avg_per_patient': revenue / patient_count if patient_count > 0 else 0,
        })

    doctor_data.sort(key=lambda x: x['total_revenue'], reverse=True)

    context = {
        'doctors': doctor_data,
        'total_revenue': total_revenue,
        'total_appointments': total_appointments,
        'total_patients': total_patients,
        'start_date': start_date,
        'end_date': end_date,
        'start_date_str': start_date.strftime('%Y-%m-%d'),
        'end_date_str': end_date.strftime('%Y-%m-%d'),
        'start_date_display': start_date.strftime('%b %d, %Y'),
        'end_date_display': end_date.strftime('%b %d, %Y'),
    }
    return render(request, 'reports/doctor_performance.html', context)

