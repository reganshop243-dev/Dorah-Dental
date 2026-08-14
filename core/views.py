from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import models
from django.http import JsonResponse
from .models import UserProfile
from .otp_service import OTPService
from datetime import timedelta


# ====================
# HELPER FUNCTION - Clean Doctor Names
# ====================

def clean_doctor_name(first_name, last_name, username=""):
    """Clean doctor name - remove any existing 'Dr.' prefixes"""
    # Combine names
    if first_name and last_name:
        name = f"{first_name} {last_name}"
    elif first_name:
        name = first_name
    elif last_name:
        name = last_name
    else:
        name = username or "Doctor"
    
    # Remove all "Dr." prefixes (case insensitive)
    import re
    name = re.sub(r'^Dr\.\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s+Dr\.\s*', ' ', name, flags=re.IGNORECASE)
    
    # Remove extra spaces
    name = ' '.join(name.split())
    
    return name


def login_view(request):
    """Custom login view with username OR phone number login"""
    if request.user.is_authenticated:
        # Check if user needs OTP verification
        if not request.user.profile.phone_verified:
            # If OTP not sent yet, send it
            if not request.user.profile.otp_code:
                otp_service = OTPService()
                otp_service.create_and_send_otp(request.user)
            return redirect('core:otp_verify')
        return redirect_to_dashboard(request.user)
    
    if request.method == 'POST':
        username_or_phone = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        # Try to find user by username or phone
        user = None
        
        # First try username
        try:
            user = User.objects.get(username=username_or_phone)
        except User.DoesNotExist:
            # Try phone number
            try:
                profile = UserProfile.objects.get(phone=username_or_phone)
                user = profile.user
            except UserProfile.DoesNotExist:
                pass
        
        if user:
            # Authenticate with password
            authenticated_user = authenticate(request, username=user.username, password=password)
            if authenticated_user:
                login(request, authenticated_user)
                
                # Check if user has phone number for OTP
                if not user.profile.phone:
                    messages.warning(request, 'No phone number registered for OTP. Please contact administrator.')
                    return render(request, 'core/login.html')
                
                # Send OTP
                otp_service = OTPService()
                success, message = otp_service.create_and_send_otp(user)
                
                if success:
                    messages.info(request, f'OTP sent to your registered phone number ({user.profile.phone})')
                    return redirect('core:otp_verify')
                else:
                    messages.error(request, f'Failed to send OTP: {message}')
                    return render(request, 'core/login.html')
            else:
                messages.error(request, 'Invalid password')
        else:
            messages.error(request, 'Invalid username or phone number')
    
    return render(request, 'core/login.html')


def redirect_to_dashboard(user):
    """Redirect users based on their role"""
    try:
        profile = user.profile
        role = profile.role
        
        # Role-based redirects
        if role == 'admin':
            return redirect('core:admin_dashboard')
        elif role == 'doctor':
            return redirect('core:doctor_dashboard')
        elif role == 'accountant':
            return redirect('core:accountant_dashboard')
        elif role == 'receptionist':
            return redirect('core:receptionist_dashboard')
        else:
            return redirect('core:dashboard')
    except:
        # If no profile, redirect to default dashboard
        return redirect('core:dashboard')


def logout_view(request):
    """Custom logout view"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('core:login')


@login_required
def otp_verify_view(request):
    """View for OTP verification after login"""
    # If already verified, redirect to dashboard
    if request.user.profile.phone_verified:
        return redirect_to_dashboard(request.user)
    
    # Check if OTP has expired (5 minutes)
    profile = request.user.profile
    if profile.otp_code and profile.otp_created_at:
        from django.utils import timezone
        time_diff = timezone.now() - profile.otp_created_at
        if time_diff.total_seconds() > 300:  # 5 minutes
            # OTP expired - clear it
            profile.otp_code = None
            profile.otp_created_at = None
            profile.save()
            messages.warning(request, 'Your OTP has expired. Please request a new one.')
            return redirect('core:otp_send')
    
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code', '').strip()
        
        # DEBUG: Allow 000000 as master OTP for testing
        if otp_code == '000000':
            profile = request.user.profile
            profile.phone_verified = True
            profile.otp_code = None
            profile.otp_created_at = None
            profile.otp_attempts = 0
            profile.save()
            messages.success(request, 'OTP verified successfully (debug mode)!')
            return redirect_to_dashboard(request.user)
        
        if not otp_code or len(otp_code) != 6 or not otp_code.isdigit():
            messages.error(request, 'Please enter a valid 6-digit OTP')
            return render(request, 'core/otp_verify.html')
        
        # Verify OTP
        otp_service = OTPService()
        success, message = otp_service.verify_otp(request.user, otp_code)
        
        if success:
            messages.success(request, 'OTP verified successfully!')
            return redirect_to_dashboard(request.user)
        else:
            messages.error(request, message)
            # Check if attempts exceeded
            if request.user.profile.otp_attempts >= 3:
                # Reset OTP and allow resend
                profile = request.user.profile
                profile.otp_code = None
                profile.otp_created_at = None
                profile.save()
                messages.warning(request, 'Too many failed attempts. Please request a new OTP.')
                return redirect('core:otp_send')
    
    # GET request - show OTP form
    return render(request, 'core/otp_verify.html')


@login_required
def otp_send_view(request):
    """Send OTP to user's phone"""
    # If already verified, redirect to dashboard
    if request.user.profile.phone_verified:
        return redirect_to_dashboard(request.user)
    
    # Check if OTP exists and is still valid
    profile = request.user.profile
    otp_exists = profile.otp_code and profile.otp_created_at
    
    if otp_exists:
        from django.utils import timezone
        time_diff = timezone.now() - profile.otp_created_at
        if time_diff.total_seconds() <= 300:  # Still valid (5 minutes)
            # OTP still valid - redirect to verify page
            messages.info(request, 'Your OTP is still valid. Please enter it below.')
            return redirect('core:otp_verify')
    
    if request.method == 'POST':
        # Check if user can request OTP (once per day)
        if not profile.can_request_otp():
            # Check if OTP has expired - if expired, allow resend
            if profile.otp_code and profile.otp_created_at:
                from django.utils import timezone
                time_diff = timezone.now() - profile.otp_created_at
                if time_diff.total_seconds() > 300:  # Expired
                    # Allow resend for expired OTP - reset the cooldown
                    profile.last_otp_sent = timezone.now() - timedelta(days=1)
                    profile.save()
                else:
                    messages.warning(request, 'OTP already sent. Please check your phone or enter the code below.')
                    return redirect('core:otp_verify')
            else:
                messages.warning(request, 'OTP already sent today. Please check your phone.')
                return redirect('core:otp_verify')
        
        # Force reset any existing OTP
        profile.otp_code = None
        profile.otp_created_at = None
        profile.otp_attempts = 0
        profile.save()
        
        # Send new OTP
        otp_service = OTPService()
        success, message = otp_service.create_and_send_otp(request.user)
        
        if success:
            messages.success(request, f'OTP sent to your registered phone number ({request.user.profile.phone})')
            return redirect('core:otp_verify')
        else:
            messages.error(request, message)
    
    # GET request - show send OTP page
    return render(request, 'core/otp_send.html')


# ====================
# DASHBOARD VIEWS BY ROLE - WITH OTP REQUIRED
# ====================

def otp_required(function):
    """Decorator to ensure user has verified OTP"""
    def wrap(request, *args, **kwargs):
        if request.user.is_authenticated:
            if not request.user.profile.phone_verified:
                messages.warning(request, 'Please verify your phone number first.')
                return redirect('core:otp_verify')
        return function(request, *args, **kwargs)
    return wrap


@login_required
@otp_required
def dashboard(request):
    """General dashboard for all users"""
    from patients.models import Patient
    from appointments.models import Appointment, Doctor, Service
    from django.utils import timezone
    from datetime import date
    
    today = date.today()
    
    context = {
        'total_patients': Patient.objects.filter(is_active=True).count(),
        'total_doctors': Doctor.objects.filter(is_active=True).count(),
        'total_services': Service.objects.filter(is_active=True).count(),
        'today_appointments': Appointment.objects.filter(appointment_date=today).count(),
        'upcoming_appointments': Appointment.objects.filter(
            appointment_date__gte=today,
            status__in=['scheduled', 'checked_in']
        ).count(),
    }
    return render(request, 'core/dashboard.html', context)


@login_required
@otp_required
def admin_dashboard(request):
    """Admin dashboard with full access to all data"""
    from patients.models import Patient
    from appointments.models import Appointment, Doctor, Service, Treatment
    from billing.models import Invoice, Payment
    from django.utils import timezone
    from datetime import date, timedelta
    from django.db import models as django_models
    
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    
    # ==================== SYSTEM STATS ====================
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    total_patients = Patient.objects.filter(is_active=True).count()
    total_doctors = Doctor.objects.filter(is_active=True).count()
    total_services = Service.objects.filter(is_active=True).count()
    
    # ==================== USERS LIST ====================
    users = User.objects.all().select_related('profile').order_by('-date_joined')[:20]
    
    # ==================== SERVICES LIST ====================
    services = Service.objects.filter(is_active=True).order_by('name')[:20]
    
    # ==================== DOCTORS LIST ====================
    doctors = Doctor.objects.filter(is_active=True).order_by('name')[:20]
    
    # ==================== APPOINTMENT STATS ====================
    today_appointments = Appointment.objects.filter(appointment_date=today).select_related('patient', 'doctor', 'service')
    today_appointments_count = today_appointments.count()
    
    upcoming_appointments = Appointment.objects.filter(
        appointment_date__gte=today,
        status__in=['scheduled', 'checked_in']
    ).select_related('patient', 'doctor', 'service').order_by('appointment_date', 'appointment_time')[:10]
    
    total_appointments = Appointment.objects.count()
    completed_appointments = Appointment.objects.filter(status='completed').count()
    cancelled_appointments = Appointment.objects.filter(status='cancelled').count()
    
    # Appointments by status
    appointment_status_counts = Appointment.objects.values('status').annotate(count=django_models.Count('id'))
    status_dict = {item['status']: item['count'] for item in appointment_status_counts}
    
    # ==================== FINANCIAL STATS ====================
    total_revenue = Invoice.objects.filter(status='paid').aggregate(
        django_models.Sum('total_amount')
    )['total_amount__sum'] or 0
    
    daily_revenue = Invoice.objects.filter(
        status='paid',
        payment_date__date=today
    ).aggregate(django_models.Sum('total_amount'))['total_amount__sum'] or 0
    
    weekly_revenue = Invoice.objects.filter(
        status='paid',
        payment_date__date__gte=start_of_week
    ).aggregate(django_models.Sum('total_amount'))['total_amount__sum'] or 0
    
    monthly_revenue = Invoice.objects.filter(
        status='paid',
        payment_date__date__gte=start_of_month
    ).aggregate(django_models.Sum('total_amount'))['total_amount__sum'] or 0
    
    total_invoices = Invoice.objects.count()
    paid_invoices = Invoice.objects.filter(status='paid').count()
    pending_invoices = Invoice.objects.filter(
        status__in=['draft', 'sent', 'partially_paid']
    ).count()
    overdue_invoices = Invoice.objects.filter(status='overdue').count()
    
    total_outstanding = Invoice.objects.filter(
        status__in=['draft', 'sent', 'partially_paid', 'overdue']
    ).aggregate(django_models.Sum('balance_due'))['balance_due__sum'] or 0
    
    recent_payments = Payment.objects.filter(
        status='completed'
    ).select_related('invoice', 'invoice__patient').order_by('-payment_date')[:10]
    
    # ==================== PATIENT STATS ====================
    new_patients_today = Patient.objects.filter(
        registered_at__date=today
    ).count()
    
    new_patients_this_month = Patient.objects.filter(
        registered_at__date__gte=start_of_month
    ).count()
    
    recent_patients = Patient.objects.filter(
        is_active=True
    ).order_by('-registered_at')[:10]
    
    top_patients = Invoice.objects.filter(
        status='paid'
    ).values(
        'patient__id', 
        'patient__first_name', 
        'patient__last_name'
    ).annotate(
        total_spent=django_models.Sum('total_amount'),
        visit_count=django_models.Count('id')
    ).order_by('-total_spent')[:10]
    
    # ==================== INVENTORY ALERTS ====================
    from inventory.models import InventoryItem
    low_stock_items = InventoryItem.objects.filter(
        is_active=True,
        quantity__lte=django_models.F('min_quantity')
    ).order_by('quantity')[:10]
    
    out_of_stock_items = InventoryItem.objects.filter(
        is_active=True,
        quantity=0
    ).count()
    
    # ==================== CONTEXT ====================
    context = {
        # System Stats
        'total_users': total_users,
        'active_users': active_users,
        'total_patients': total_patients,
        'total_doctors': total_doctors,
        'total_services': total_services,
        
        # Lists
        'users': users,
        'services': services,
        'doctors': doctors,
        
        # Appointment Stats
        'today_appointments': today_appointments,
        'today_appointments_count': today_appointments_count,
        'upcoming_appointments': upcoming_appointments,
        'total_appointments': total_appointments,
        'completed_appointments': completed_appointments,
        'cancelled_appointments': cancelled_appointments,
        'status_dict': status_dict,
        
        # Financial Stats
        'total_revenue': total_revenue,
        'daily_revenue': daily_revenue,
        'weekly_revenue': weekly_revenue,
        'monthly_revenue': monthly_revenue,
        'total_invoices': total_invoices,
        'paid_invoices': paid_invoices,
        'pending_invoices': pending_invoices,
        'overdue_invoices': overdue_invoices,
        'total_outstanding': total_outstanding,
        'recent_payments': recent_payments,
        
        # Patient Stats
        'new_patients_today': new_patients_today,
        'new_patients_this_month': new_patients_this_month,
        'recent_patients': recent_patients,
        'top_patients': top_patients,
        
        # Inventory Alerts
        'low_stock_items': low_stock_items,
        'out_of_stock_items': out_of_stock_items,
        
        'today': today,
    }
    return render(request, 'core/admin_dashboard.html', context)


@login_required
@otp_required
def doctor_dashboard(request):
    """Doctor dashboard showing their appointments and patients"""
    from appointments.models import Appointment, Treatment
    from django.utils import timezone
    from datetime import date
    
    today = date.today()
    user_profile = request.user.profile
    
    # Get the doctor associated with this user
    doctor = user_profile.doctor
    
    if doctor:
        # Show only this doctor's appointments
        today_appointments = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=today
        ).order_by('appointment_time')
        
        upcoming_appointments = Appointment.objects.filter(
            doctor=doctor,
            appointment_date__gte=today,
            status__in=['scheduled', 'checked_in']
        ).order_by('appointment_date', 'appointment_time')[:20]
        
        treatments_count = Treatment.objects.filter(doctor=doctor).count()
        
        context = {
            'doctor': doctor,
            'today_appointments': today_appointments,
            'upcoming_appointments': upcoming_appointments,
            'treatments_count': treatments_count,
            'today': today,
        }
    else:
        context = {
            'doctor': None,
            'today_appointments': [],
            'upcoming_appointments': [],
            'treatments_count': 0,
            'today': today,
        }
    
    return render(request, 'core/doctor_dashboard.html', context)


@login_required
@otp_required
def receptionist_dashboard(request):
    """Receptionist dashboard for managing appointments and patients"""
    from patients.models import Patient
    from appointments.models import Appointment
    from django.utils import timezone
    from datetime import date
    
    today = date.today()
    
    # Today's appointments
    today_appointments = Appointment.objects.filter(
        appointment_date=today
    ).order_by('appointment_time')
    
    # New patients today
    new_patients_today = Patient.objects.filter(
        registered_at__date=today
    ).count()
    
    # Walk-in appointments (no_show or scheduled today)
    walk_ins = Appointment.objects.filter(
        appointment_date=today,
        status='scheduled'
    ).count()
    
    context = {
        'today_appointments': today_appointments,
        'new_patients_today': new_patients_today,
        'walk_ins': walk_ins,
        'today': today,
    }
    return render(request, 'core/receptionist_dashboard.html', context)


@login_required
@otp_required
def accountant_dashboard(request):
    """Accountant dashboard for financial management"""
    from billing.models import Invoice, Payment
    from django.utils import timezone
    from datetime import date, timedelta
    from django.db.models import Sum
    
    today = date.today()
    start_of_month = today.replace(day=1)
    
    # Monthly revenue
    monthly_revenue = Invoice.objects.filter(
        status='paid',
        payment_date__date__gte=start_of_month
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Pending payments
    pending_invoices = Invoice.objects.filter(
        status__in=['draft', 'sent', 'partially_paid']
    )
    pending_total = pending_invoices.aggregate(Sum('balance_due'))['balance_due__sum'] or 0
    
    # Recent transactions
    recent_payments = Payment.objects.filter(
        status='completed'
    ).order_by('-payment_date')[:10]
    
    # Daily revenue
    daily_revenue = Invoice.objects.filter(
        status='paid',
        payment_date__date=today
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    context = {
        'monthly_revenue': monthly_revenue,
        'pending_total': pending_total,
        'pending_invoices': pending_invoices,
        'recent_payments': recent_payments,
        'daily_revenue': daily_revenue,
        'today': today,
    }
    return render(request, 'core/accountant_dashboard.html', context)


# ====================
# USER MANAGEMENT VIEWS
# ====================

@login_required
def user_list(request):
    """List all users with their roles"""
    if request.user.profile.role != 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('core:dashboard')
    
    users = User.objects.all().select_related('profile').order_by('-date_joined')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        users = users.filter(
            models.Q(username__icontains=search) |
            models.Q(first_name__icontains=search) |
            models.Q(last_name__icontains=search) |
            models.Q(email__icontains=search) |
            models.Q(profile__role__icontains=search)
        )
    
    context = {
        'users': users,
        'search_query': search,
    }
    return render(request, 'core/user_list.html', context)


@login_required
def user_add(request):
    """Add a new user with role assignment"""
    if request.user.profile.role != 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('core:dashboard')
    
    from appointments.models import Doctor
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role')
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        
        # Validate
        if not username:
            messages.error(request, 'Username is required')
            return render(request, 'core/user_add.html', {'roles': UserProfile.ROLE_CHOICES})
        
        if not password:
            messages.error(request, 'Password is required')
            return render(request, 'core/user_add.html', {'roles': UserProfile.ROLE_CHOICES})
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'core/user_add.html', {'roles': UserProfile.ROLE_CHOICES})
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'core/user_add.html', {'roles': UserProfile.ROLE_CHOICES})
        
        if email and User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
            return render(request, 'core/user_add.html', {'roles': UserProfile.ROLE_CHOICES})
        
        # Validate phone is required for OTP
        if not phone:
            messages.error(request, 'Phone number is required for OTP verification')
            return render(request, 'core/user_add.html', {'roles': UserProfile.ROLE_CHOICES})
        
        if not role:
            messages.error(request, 'Please select a role')
            return render(request, 'core/user_add.html', {'roles': UserProfile.ROLE_CHOICES})
        
        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email,
                is_active=is_active
            )
            
            # Update profile with role
            profile = user.profile
            profile.role = role
            profile.phone = phone
            profile.address = address
            profile.is_active = is_active
            profile.phone_verified = False  # Phone needs to be verified via OTP
            
            # If role is doctor, create a doctor profile
            if role == 'doctor':
                # ✅ FIX: Clean the name before saving
                clean_name = clean_doctor_name(first_name, last_name, username)
                
                doctor_option = request.POST.get('doctor_option', 'auto')
                
                if doctor_option == 'existing':
                    doctor_id = request.POST.get('doctor_link')
                    if doctor_id:
                        try:
                            doctor = Doctor.objects.get(pk=doctor_id)
                            profile.doctor = doctor
                        except Doctor.DoesNotExist:
                            doctor = Doctor.objects.create(
                                name=clean_name,  # ✅ FIXED: No "Dr." hardcoded
                                specialization=request.POST.get('specialization', 'General Dentistry'),
                                phone=phone or '',
                                email=email or '',
                                is_active=True
                            )
                            profile.doctor = doctor
                    else:
                        doctor = Doctor.objects.create(
                            name=clean_name,  # ✅ FIXED: No "Dr." hardcoded
                            specialization=request.POST.get('specialization', 'General Dentistry'),
                            phone=phone or '',
                            email=email or '',
                            is_active=True
                        )
                        profile.doctor = doctor
                else:
                    doctor = Doctor.objects.create(
                        name=clean_name,  # ✅ FIXED: No "Dr." hardcoded
                        specialization=request.POST.get('specialization', 'General Dentistry'),
                        phone=phone or '',
                        email=email or '',
                        is_active=True
                    )
                    profile.doctor = doctor
                
                messages.info(request, f'Doctor profile created for {doctor.name}')
            
            profile.save()
            
            messages.success(request, f'User "{username}" created successfully with role: {profile.get_role_display()}')
            messages.info(request, f'User will need to verify their phone ({phone}) via OTP on first login.')
            return redirect('core:user_list')
            
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
    
    from appointments.models import Doctor
    doctors = Doctor.objects.filter(is_active=True)
    
    return render(request, 'core/user_add.html', {
        'roles': UserProfile.ROLE_CHOICES,
        'doctors': doctors,
    })


@login_required
def user_edit(request, pk):
    """Edit user details and role"""
    if request.user.profile.role != 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('core:dashboard')
    
    user = get_object_or_404(User, pk=pk)
    profile = user.profile
    
    # Get all doctors for optional linking
    from appointments.models import Doctor
    all_doctors = Doctor.objects.filter(is_active=True)
    
    if request.method == 'POST':
        try:
            # Get form data
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            
            # Update user fields
            user.first_name = first_name
            user.last_name = last_name
            user.email = request.POST.get('email', '').strip()
            user.is_active = request.POST.get('is_active') == 'on'
            
            # Update profile fields
            new_role = request.POST.get('role')
            profile.role = new_role
            profile.phone = request.POST.get('phone', '').strip()
            profile.address = request.POST.get('address', '').strip()
            profile.is_active = request.POST.get('is_active') == 'on'
            
            # Optional: Handle doctor linking ONLY if role is doctor
            if new_role == 'doctor':
                # ✅ FIX: Clean the name before saving
                clean_name = clean_doctor_name(first_name, last_name, user.username)
                
                doctor_option = request.POST.get('doctor_option', 'auto')
                
                if doctor_option == 'existing':
                    doctor_id = request.POST.get('doctor_link')
                    if doctor_id:
                        try:
                            doctor = Doctor.objects.get(pk=doctor_id)
                            profile.doctor = doctor
                        except Doctor.DoesNotExist:
                            messages.warning(request, 'Selected doctor not found. Creating new one.')
                            doctor = Doctor.objects.create(
                                name=clean_name,  # ✅ FIXED: No "Dr." hardcoded
                                phone=profile.phone or '',
                                email=user.email or '',
                                specialization=request.POST.get('specialization', 'General Dentistry'),
                                is_active=True
                            )
                            profile.doctor = doctor
                    else:
                        doctor = Doctor.objects.create(
                            name=clean_name,  # ✅ FIXED: No "Dr." hardcoded
                            phone=profile.phone or '',
                            email=user.email or '',
                            specialization=request.POST.get('specialization', 'General Dentistry'),
                            is_active=True
                        )
                        profile.doctor = doctor
                else:
                    doctor = Doctor.objects.create(
                        name=clean_name,  # ✅ FIXED: No "Dr." hardcoded
                        phone=profile.phone or '',
                        email=user.email or '',
                        specialization=request.POST.get('specialization', 'General Dentistry'),
                        is_active=True
                    )
                    profile.doctor = doctor
                    messages.info(request, f'Auto-created doctor profile for {doctor.name}')
            else:
                # If role is not doctor, remove doctor link
                profile.doctor = None
            
            # Update password if provided
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if new_password:
                if new_password != confirm_password:
                    messages.error(request, 'Passwords do not match')
                    return render(request, 'core/user_edit.html', {
                        'user': user,
                        'profile': profile,
                        'roles': UserProfile.ROLE_CHOICES,
                        'doctors': all_doctors,
                    })
                user.set_password(new_password)
            
            user.save()
            profile.save()
            
            messages.success(request, f'User "{user.username}" updated successfully with role: {profile.get_role_display()}')
            return redirect('core:user_list')
            
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
    
    context = {
        'user': user,
        'profile': profile,
        'roles': UserProfile.ROLE_CHOICES,
        'doctors': all_doctors,
        'current_doctor': profile.doctor,
    }
    return render(request, 'core/user_edit.html', context)


@login_required
def user_delete(request, pk):
    """Delete a user (soft delete)"""
    if request.user.profile.role != 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('core:dashboard')
    
    user = get_object_or_404(User, pk=pk)
    
    # Prevent deleting yourself
    if user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('core:user_list')
    
    if request.method == 'POST':
        try:
            # Soft delete - just deactivate
            user.is_active = False
            user.save()
            
            # Also deactivate profile
            profile = user.profile
            profile.is_active = False
            profile.save()
            
            messages.success(request, f'User "{user.username}" has been deactivated.')
        except Exception as e:
            messages.error(request, f'Error deactivating user: {str(e)}')
        
        return redirect('core:user_list')
    
    return render(request, 'core/user_delete.html', {'user': user})


@login_required
def user_activate(request, pk):
    """Activate a user (re-activate after soft delete)"""
    if request.user.profile.role != 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('core:dashboard')
    
    user = get_object_or_404(User, pk=pk)
    
    try:
        user.is_active = True
        user.save()
        
        profile = user.profile
        profile.is_active = True
        profile.save()
        
        messages.success(request, f'User "{user.username}" has been activated.')
    except Exception as e:
        messages.error(request, f'Error activating user: {str(e)}')
    
    return redirect('core:user_list')


# ====================
# ROLE MANAGEMENT
# ====================

@login_required
def role_management(request):
    """View all users grouped by role"""
    if request.user.profile.role != 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('core:dashboard')
    
    from django.db.models import Count
    
    # Get all users with their roles
    users = User.objects.all().select_related('profile').order_by('profile__role', 'username')
    
    # Group users by role
    roles = {}
    for user in users:
        role = user.profile.role
        if role not in roles:
            roles[role] = []
        roles[role].append(user)
    
    # Get role counts
    role_counts = UserProfile.objects.values('role').annotate(count=Count('id'))
    role_stats = {item['role']: item['count'] for item in role_counts}
    
    context = {
        'roles': roles,
        'role_stats': role_stats,
        'role_choices': UserProfile.ROLE_CHOICES,
    }
    return render(request, 'core/role_management.html', context)


# ====================
# REVENUE / FINANCIAL DASHBOARD
# ====================

@login_required
@otp_required
def revenue_dashboard(request):
    """Financial dashboard showing revenue, payments, and reports with date filters"""
    from billing.models import Invoice, Payment
    from appointments.models import Appointment
    from django.utils import timezone
    from datetime import date, timedelta, datetime
    from django.db.models import Sum, Count, Q
    
    # Get date filters from request
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')
    period = request.GET.get('period', 'this_month')
    
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    start_of_year = today.replace(month=1, day=1)
    
    # Determine date range based on period or custom dates
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            period = 'custom'
        except ValueError:
            start_date = start_of_month
            end_date = today
    else:
        if period == 'today':
            start_date = today
            end_date = today
        elif period == 'this_week':
            start_date = start_of_week
            end_date = today
        elif period == 'this_month':
            start_date = start_of_month
            end_date = today
        elif period == 'this_year':
            start_date = start_of_year
            end_date = today
        elif period == 'all':
            start_date = date(2000, 1, 1)
            end_date = today
        else:
            start_date = start_of_month
            end_date = today
            period = 'this_month'
    
    # Format dates for display
    start_date_display = start_date.strftime('%b %d, %Y')
    end_date_display = end_date.strftime('%b %d, %Y')
    
    # ============================================================
    # GET ALL INVOICES FOR THE PERIOD
    # ============================================================
    period_invoices = Invoice.objects.filter(
        issue_date__gte=start_date,
        issue_date__lte=end_date
    )
    
    # Period Revenue
    period_revenue = period_invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    period_paid = period_invoices.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    period_balance = period_invoices.aggregate(Sum('balance_due'))['balance_due__sum'] or 0
    
    # Total revenue (all time)
    total_revenue = Invoice.objects.aggregate(
        Sum('total_amount')
    )['total_amount__sum'] or 0
    
    # Total paid (all time)
    total_paid = Invoice.objects.aggregate(
        Sum('amount_paid')
    )['amount_paid__sum'] or 0
    
    # Daily revenue (today)
    daily_revenue = Invoice.objects.filter(
        issue_date=today
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Weekly revenue
    weekly_revenue = Invoice.objects.filter(
        issue_date__gte=start_of_week,
        issue_date__lte=today
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Monthly revenue
    monthly_revenue = Invoice.objects.filter(
        issue_date__gte=start_of_month,
        issue_date__lte=today
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Yearly revenue
    yearly_revenue = Invoice.objects.filter(
        issue_date__gte=start_of_year,
        issue_date__lte=today
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # Outstanding balance (all time)
    total_outstanding = Invoice.objects.aggregate(
        Sum('balance_due')
    )['balance_due__sum'] or 0
    
    # ============================================================
    # INVOICE STATUS BREAKDOWN
    # ============================================================
    total_invoices = period_invoices.count()
    paid_invoices = period_invoices.filter(status='paid').count()
    partially_paid_invoices = period_invoices.filter(status='partially_paid').count()
    pending_invoices = period_invoices.filter(
        status__in=['draft', 'sent']
    ).count()
    overdue_invoices = period_invoices.filter(status='overdue').count()
    
    # ============================================================
    # TOP PATIENTS
    # ============================================================
    top_patients = period_invoices.values(
        'patient__id', 
        'patient__first_name', 
        'patient__last_name'
    ).annotate(
        total_spent=Sum('total_amount'),
        total_paid=Sum('amount_paid'),
        total_balance=Sum('balance_due'),
        visit_count=Count('id')
    ).order_by('-total_spent')[:10]
    
    # ============================================================
    # RECENT PAYMENTS - FIXED: removed __date lookup
    # ============================================================
    recent_payments = Payment.objects.filter(
        payment_date__gte=start_date,
        payment_date__lte=end_date
    ).select_related('invoice', 'invoice__patient').order_by('-payment_date')[:10]
    
    # ============================================================
    # MONTHLY REVENUE
    # ============================================================
    monthly_data = []
    for i in range(11, -1, -1):
        month_date = today.replace(day=1) - timedelta(days=30*i)
        month_start = month_date.replace(day=1)
        if i == 0:
            month_end = today
        else:
            next_month = month_date.replace(day=28) + timedelta(days=4)
            month_end = next_month - timedelta(days=next_month.day)
        
        month_invoices = Invoice.objects.filter(
            issue_date__gte=month_start,
            issue_date__lte=month_end
        )
        
        revenue = month_invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        paid = month_invoices.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        
        monthly_data.append({
            'month': month_date.strftime('%B'),
            'year': month_date.year,
            'revenue': revenue,
            'paid': paid,
        })
    
    max_monthly_revenue = max([d['revenue'] for d in monthly_data]) if monthly_data else 1
    
    context = {
        'total_revenue': total_revenue,
        'total_paid': total_paid,
        'daily_revenue': daily_revenue,
        'weekly_revenue': weekly_revenue,
        'monthly_revenue': monthly_revenue,
        'yearly_revenue': yearly_revenue,
        'total_outstanding': total_outstanding,
        'period_revenue': period_revenue,
        'period_paid': period_paid,
        'period_balance': period_balance,
        'total_invoices': total_invoices,
        'paid_invoices': paid_invoices,
        'partially_paid_invoices': partially_paid_invoices,
        'pending_invoices': pending_invoices,
        'overdue_invoices': overdue_invoices,
        'recent_payments': recent_payments,
        'top_patients': top_patients,
        'monthly_data': monthly_data,
        'max_monthly_revenue': max_monthly_revenue,
        'today': today,
        'start_date': start_date,
        'end_date': end_date,
        'start_date_display': start_date_display,
        'end_date_display': end_date_display,
        'period': period,
        'start_date_str': start_date.strftime('%Y-%m-%d'),
        'end_date_str': end_date.strftime('%Y-%m-%d'),
    }
    
    return render(request, 'core/revenue_dashboard.html', context)


@login_required
def reset_user_otp(request, pk):
    """Admin function to reset a user's OTP cooldown"""
    if request.user.profile.role != 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('core:dashboard')
    
    user = get_object_or_404(User, pk=pk)
    from django.utils import timezone
    
    user.profile.last_otp_sent = timezone.now() - timedelta(days=2)
    user.profile.otp_attempts = 0
    user.profile.otp_code = None
    user.profile.otp_created_at = None
    user.profile.save()
    
    messages.success(request, f'OTP cooldown reset for {user.username}')
    return redirect('core:user_list')


@login_required
def company_settings(request):
    """Company settings view"""
    from .models import CompanySettings
    
    # Only admin can access
    if request.user.profile.role != 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('core:dashboard')
    
    settings = CompanySettings.get_settings()
    
    if request.method == 'POST':
        try:
            # Business Info
            settings.business_name = request.POST.get('business_name')
            settings.business_short_name = request.POST.get('business_short_name')
            settings.tagline = request.POST.get('tagline', '')
            settings.description = request.POST.get('description', '')
            
            # Contact Info
            settings.phone = request.POST.get('phone')
            settings.email = request.POST.get('email')
            settings.website = request.POST.get('website', '')
            settings.address = request.POST.get('address')
            
            # Social Media
            settings.facebook = request.POST.get('facebook', '')
            settings.twitter = request.POST.get('twitter', '')
            settings.instagram = request.POST.get('instagram', '')
            settings.youtube = request.POST.get('youtube', '')
            
            # Business Hours
            settings.monday_hours = request.POST.get('monday_hours', '')
            settings.tuesday_hours = request.POST.get('tuesday_hours', '')
            settings.wednesday_hours = request.POST.get('wednesday_hours', '')
            settings.thursday_hours = request.POST.get('thursday_hours', '')
            settings.friday_hours = request.POST.get('friday_hours', '')
            settings.saturday_hours = request.POST.get('saturday_hours', '')
            settings.sunday_hours = request.POST.get('sunday_hours', '')
            
            # Currency and Region
            settings.currency = request.POST.get('currency', 'UGX')
            settings.currency_symbol = request.POST.get('currency_symbol', 'UGX')
            settings.timezone = request.POST.get('timezone', 'Africa/Nairobi')
            settings.country = request.POST.get('country', 'Uganda')
            
            # Tax Settings
            tax_rate = request.POST.get('tax_rate', '0')
            try:
                settings.tax_rate = float(tax_rate)
            except:
                settings.tax_rate = 0
            settings.tax_id = request.POST.get('tax_id', '')
            
            # Invoice Settings
            settings.invoice_prefix = request.POST.get('invoice_prefix', 'INV-')
            settings.invoice_footer = request.POST.get('invoice_footer', '')
            
            # Notification Settings
            settings.notification_email = request.POST.get('notification_email', '')
            settings.notification_phone = request.POST.get('notification_phone', '')
            
            # Logo upload
            if request.FILES.get('logo'):
                if settings.logo:
                    settings.logo.delete()
                settings.logo = request.FILES.get('logo')
            
            if request.FILES.get('favicon'):
                if settings.favicon:
                    settings.favicon.delete()
                settings.favicon = request.FILES.get('favicon')
            
            settings.save()
            
            messages.success(request, 'Company settings updated successfully!')
            return redirect('core:company_settings')
            
        except Exception as e:
            messages.error(request, f'Error updating settings: {str(e)}')
    
    context = {
        'settings': settings,
    }
    return render(request, 'core/company_settings.html', context)