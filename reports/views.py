from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, Q
from datetime import date, timedelta, datetime
from billing.models import Invoice
from appointments.models import Appointment, Doctor
from patients.models import Patient
from django.utils import timezone


@login_required
def aging_report(request):
    """Accounts Receivable Aging Report"""
    from django.db.models import Sum, Q
    
    # Get date range
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
    
    # Get all outstanding invoices (not fully paid)
    invoices = Invoice.objects.filter(
        Q(status='partially_paid') | Q(status='overdue') | Q(status='sent') | Q(status='draft')
    )
    
    # Apply date filter
    invoices = invoices.filter(issue_date__lte=end_date)
    
    # Calculate aging
    aging_data = {
        'zero_thirty': 0,
        'thirty_sixty': 0,
        'sixty_ninety': 0,
        'over_90': 0,
        'zero_thirty_count': 0,
        'thirty_sixty_count': 0,
        'sixty_ninety_count': 0,
        'over_90_count': 0,
        'invoices': [],
        'total_outstanding': 0,
        'total_amount': 0,
        'total_paid': 0,
        'invoices_count': 0,
    }
    
    for invoice in invoices:
        if invoice.issue_date:
            age_days = (end_date - invoice.issue_date).days
            balance = invoice.balance_due or 0
            
            if balance > 0:
                invoice.age_days = age_days
                invoice.patient_name = invoice.patient_name or invoice.patient.full_name if invoice.patient else 'Unknown'
                invoice.patient_phone = invoice.patient_phone or (invoice.patient.phone if invoice.patient else '')
                
                aging_data['invoices'].append(invoice)
                aging_data['total_amount'] += invoice.total_amount or 0
                aging_data['total_paid'] += invoice.amount_paid or 0
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
    
    context = {
        'aging_data': aging_data,
        'start_date': start_date,
        'end_date': end_date,
        'start_date_str': start_date.strftime('%Y-%m-%d'),
        'end_date_str': end_date.strftime('%Y-%m-%d'),
        'start_date_display': start_date.strftime('%b %d, %Y'),
        'end_date_display': end_date.strftime('%b %d, %Y'),
    }
    
    return render(request, 'reports/aging.html', context)


@login_required
def patient_visits_report(request):
    """Patient Visit Report"""
    from django.db.models import Sum, Count, Q
    
    # Get date range
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
    
    # Get appointments in period
    appointments = Appointment.objects.filter(
        appointment_date__gte=start_date,
        appointment_date__lte=end_date,
        status='completed'
    )
    
    # Get all patients who had appointments in this period
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
        
        # Check if patient is new (first appointment in period)
        first_visit = patient_appointments.order_by('appointment_date').first()
        last_visit = patient_appointments.order_by('-appointment_date').first()
        
        # Check if patient had appointments before this period
        previous_visits = Appointment.objects.filter(
            patient=patient,
            appointment_date__lt=start_date
        ).exists()
        
        if not previous_visits and visit_count > 0:
            new_patients += 1
        else:
            returning_patients += 1
        
        # Calculate total spent from invoices
        total_spent = Invoice.objects.filter(
            patient=patient,
            issue_date__gte=start_date,
            issue_date__lte=end_date
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        patient_data.append({
            'id': patient.id,
            'full_name': patient.full_name,
            'phone': patient.phone,
            'gender': patient.gender,
            'visit_count': visit_count,
            'total_spent': total_spent,
            'avg_per_visit': total_spent / visit_count if visit_count > 0 else 0,
            'first_visit': first_visit.appointment_date if first_visit else None,
            'last_visit': last_visit.appointment_date if last_visit else None,
        })
    
    # Sort by visit count descending
    patient_data.sort(key=lambda x: x['visit_count'], reverse=True)
    
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
def doctor_performance_report(request):
    """Doctor Performance Report"""
    from django.db.models import Sum, Count, Q, Avg
    
    # Get date range
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
    
    # Get all active doctors
    doctors = Doctor.objects.filter(is_active=True)
    
    doctor_data = []
    total_revenue = 0
    total_appointments = 0
    total_patients = 0
    
    for doctor in doctors:
        # Get appointments for this doctor in period
        appointments = Appointment.objects.filter(
            doctor=doctor,
            appointment_date__gte=start_date,
            appointment_date__lte=end_date,
            status='completed'
        )
        
        appointment_count = appointments.count()
        patient_count = appointments.values('patient').distinct().count()
        
        # Get revenue from invoices for this doctor's appointments
        invoice_ids = appointments.values_list('id', flat=True)
        revenue = Invoice.objects.filter(
            appointment__in=invoice_ids,
            issue_date__gte=start_date,
            issue_date__lte=end_date
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
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
    
    # Sort by revenue descending
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