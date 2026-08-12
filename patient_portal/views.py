from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Sum, Q
from patients.models import Patient, DentalImage
from appointments.models import Appointment, Service, Doctor
from billing.models import Invoice
from .models import PatientPortalAccess, PatientPortalLog
import hashlib
import hmac
import re


# ====================
# HELPER FUNCTIONS
# ====================

def log_patient_action(patient, action, request):
    """Log patient portal activity"""
    PatientPortalLog.objects.create(
        patient=patient,
        action=action,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
    )


def generate_portal_pin():
    """Generate a random 6-digit PIN"""
    import random
    return f"{random.randint(100000, 999999)}"


# ====================
# PATIENT PORTAL LOGIN
# ====================

def patient_portal_login(request):
    """Patient portal login page"""
    if request.session.get('patient_portal_logged_in'):
        return redirect('patient_portal:dashboard')
    
    if request.method == 'POST':
        # Get login credentials
        identifier = request.POST.get('identifier', '').strip()  # Phone or Patient ID
        pin = request.POST.get('pin', '').strip()
        
        if not identifier or not pin:
            messages.error(request, 'Please enter both identifier and PIN.')
            return render(request, 'patient_portal/login.html')
        
        # Try to find patient by phone or ID
        patient = None
        
        # Try by phone
        try:
            patient = Patient.objects.get(phone=identifier, is_active=True)
        except Patient.DoesNotExist:
            pass
        
        # Try by patient ID
        if not patient:
            try:
                patient = Patient.objects.get(pk=int(identifier), is_active=True)
            except (Patient.DoesNotExist, ValueError):
                pass
        
        if not patient:
            messages.error(request, 'Invalid credentials. Please check and try again.')
            return render(request, 'patient_portal/login.html')
        
        # Check portal access
        try:
            portal_access = patient.portal_access
        except PatientPortalAccess.DoesNotExist:
            messages.error(request, 'Portal access not enabled for this patient. Please contact the clinic.')
            return render(request, 'patient_portal/login.html')
        
        # Check if locked
        if portal_access.is_locked():
            messages.error(request, f'Account locked. Please try again after {portal_access.locked_until.strftime("%I:%M %p")}.')
            return render(request, 'patient_portal/login.html')
        
        # Check if active
        if not portal_access.is_active:
            messages.error(request, 'Portal access has been disabled. Please contact the clinic.')
            return render(request, 'patient_portal/login.html')
        
        # Verify PIN
        if portal_access.portal_pin == pin:
            # Success - reset attempts
            portal_access.reset_login_attempts()
            portal_access.last_login = timezone.now()
            portal_access.save()
            
            # Set session
            request.session['patient_portal_logged_in'] = True
            request.session['patient_portal_patient_id'] = patient.id
            
            # Log the login
            log_patient_action(patient, 'Login', request)
            
            messages.success(request, f'Welcome back, {patient.full_name}!')
            return redirect('patient_portal:dashboard')
        else:
            # Failed attempt
            portal_access.login_attempts += 1
            
            # Lock after 5 failed attempts
            if portal_access.login_attempts >= 5:
                portal_access.locked_until = timezone.now() + timezone.timedelta(minutes=30)
                portal_access.save()
                messages.error(request, 'Too many failed attempts. Account locked for 30 minutes.')
            else:
                portal_access.save()
                remaining = 5 - portal_access.login_attempts
                messages.error(request, f'Invalid PIN. {remaining} attempts remaining.')
            
            log_patient_action(patient, f'Failed Login Attempt {portal_access.login_attempts}', request)
            return render(request, 'patient_portal/login.html')
    
    return render(request, 'patient_portal/login.html')


def patient_portal_logout(request):
    """Logout from patient portal"""
    patient_id = request.session.get('patient_portal_patient_id')
    if patient_id:
        try:
            patient = Patient.objects.get(pk=patient_id)
            log_patient_action(patient, 'Logout', request)
        except Patient.DoesNotExist:
            pass
    
    request.session.flush()
    messages.info(request, 'You have been logged out.')
    return redirect('patient_portal:login')


def patient_portal_required(function):
    """Decorator to check if user is logged in to patient portal"""
    def wrap(request, *args, **kwargs):
        if not request.session.get('patient_portal_logged_in'):
            messages.warning(request, 'Please login to access the patient portal.')
            return redirect('patient_portal:login')
        return function(request, *args, **kwargs)
    return wrap


# ====================
# PATIENT PORTAL VIEWS
# ====================

@patient_portal_required
def dashboard(request):
    """Patient portal dashboard"""
    patient_id = request.session.get('patient_portal_patient_id')
    patient = get_object_or_404(Patient, pk=patient_id, is_active=True)
    
    # Get statistics
    total_appointments = patient.appointment_set.count()
    upcoming_appointments = patient.appointment_set.filter(
        appointment_date__gte=timezone.now().date(),
        status__in=['scheduled', 'checked_in']
    ).count()
    
    total_invoices = patient.invoices.count()
    total_spent = patient.invoices.filter(status='paid').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Recent appointments
    recent_appointments = patient.appointment_set.all().order_by('-appointment_date')[:5]
    
    # Upcoming appointments
    upcoming_appts = patient.appointment_set.filter(
        appointment_date__gte=timezone.now().date(),
        status__in=['scheduled', 'checked_in']
    ).order_by('appointment_date', 'appointment_time')[:5]
    
    context = {
        'patient': patient,
        'total_appointments': total_appointments,
        'upcoming_appointments': upcoming_appointments,
        'total_invoices': total_invoices,
        'total_spent': total_spent,
        'recent_appointments': recent_appointments,
        'upcoming_appts': upcoming_appts,
    }
    return render(request, 'patient_portal/dashboard.html', context)


@patient_portal_required
def profile(request):
    """View patient profile (read-only)"""
    patient_id = request.session.get('patient_portal_patient_id')
    patient = get_object_or_404(Patient, pk=patient_id, is_active=True)
    
    log_patient_action(patient, 'Viewed Profile', request)
    
    context = {
        'patient': patient,
    }
    return render(request, 'patient_portal/profile.html', context)


@patient_portal_required
def appointments(request):
    """View patient appointments"""
    patient_id = request.session.get('patient_portal_patient_id')
    patient = get_object_or_404(Patient, pk=patient_id, is_active=True)
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    
    appointments = patient.appointment_set.all().order_by('-appointment_date', '-appointment_time')
    
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    
    if date_filter:
        appointments = appointments.filter(appointment_date=date_filter)
    
    log_patient_action(patient, 'Viewed Appointments', request)
    
    context = {
        'patient': patient,
        'appointments': appointments,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'status_choices': Appointment.STATUS_CHOICES,
    }
    return render(request, 'patient_portal/appointments.html', context)


@patient_portal_required
def invoices(request):
    """View patient invoices"""
    patient_id = request.session.get('patient_portal_patient_id')
    patient = get_object_or_404(Patient, pk=patient_id, is_active=True)
    
    invoices = patient.invoices.all().order_by('-issue_date')
    
    # Calculate totals
    total_amount = invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_paid = invoices.filter(status='paid').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_balance = invoices.aggregate(Sum('balance_due'))['balance_due__sum'] or 0
    
    log_patient_action(patient, 'Viewed Invoices', request)
    
    context = {
        'patient': patient,
        'invoices': invoices,
        'total_amount': total_amount,
        'total_paid': total_paid,
        'total_balance': total_balance,
    }
    return render(request, 'patient_portal/invoices.html', context)


@patient_portal_required
def services(request):
    """View available services and prices"""
    patient_id = request.session.get('patient_portal_patient_id')
    patient = get_object_or_404(Patient, pk=patient_id, is_active=True)
    
    services = Service.objects.filter(is_active=True).order_by('name')
    
    log_patient_action(patient, 'Viewed Services', request)
    
    context = {
        'patient': patient,
        'services': services,
    }
    return render(request, 'patient_portal/services.html', context)


@patient_portal_required
def dental_images(request):
    """View patient dental images"""
    patient_id = request.session.get('patient_portal_patient_id')
    patient = get_object_or_404(Patient, pk=patient_id, is_active=True)
    
    images = patient.dental_images.filter(is_active=True).order_by('-uploaded_at')
    
    log_patient_action(patient, 'Viewed Dental Images', request)
    
    context = {
        'patient': patient,
        'images': images,
    }
    return render(request, 'patient_portal/dental_images.html', context)


@patient_portal_required
def update_contact(request):
    """Update patient contact information"""
    patient_id = request.session.get('patient_portal_patient_id')
    patient = get_object_or_404(Patient, pk=patient_id, is_active=True)
    
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        
        # Validate phone
        if not phone:
            messages.error(request, 'Phone number is required.')
            return redirect('patient_portal:profile')
        
        # Update patient
        patient.phone = phone
        patient.email = email if email else None
        patient.address = address if address else None
        patient.save()
        
        log_patient_action(patient, 'Updated Contact Information', request)
        messages.success(request, 'Your contact information has been updated successfully!')
        return redirect('patient_portal:profile')
    
    return redirect('patient_portal:profile')