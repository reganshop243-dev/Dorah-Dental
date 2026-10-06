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
from django.utils.crypto import constant_time_compare
from datetime import datetime
from patients.models import Patient, DentalImage
from appointments.models import Appointment, Service, Doctor, Treatment
from billing.models import Invoice, Payment
from billing.balance_service import get_patient_outstanding_balance
from .models import (
    PatientPortalAccess, PatientPortalLog, PortalOffer, PatientConversation,
    PatientMessage, PortalNotification,
)
from .services import create_portal_notification, sync_upcoming_appointment_reminders
import hashlib
import hmac
import re


# ====================
# HELPER FUNCTIONS
# ====================

def app_download(request):
    """Public patient app download landing page for Android and iOS."""
    from django.conf import settings
    public_base = getattr(
        settings, 'PUBLIC_BASE_URL', 'https://dorah-dental-production.up.railway.app'
    ).rstrip('/')
    return render(request, 'patient_portal/app_download.html', {
        'android_app_url': getattr(settings, 'ANDROID_APP_URL', '').strip(),
        'ios_app_url': getattr(settings, 'IOS_APP_URL', '').strip(),
        'web_portal_url': f'{public_base}/portal/login/',
    })


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
        
        # Try to find patient by phone or ID. Phone numbers are normalized so
        # 0700..., +256700..., and 256700... can all identify the same patient.
        patient = None
        normalized_identifier = ''.join(ch for ch in identifier if ch.isdigit())
        if normalized_identifier.startswith('0') and len(normalized_identifier) == 10:
            normalized_identifier = '256' + normalized_identifier[1:]
        elif normalized_identifier.startswith('256'):
            pass
        elif len(normalized_identifier) == 9 and normalized_identifier.startswith('7'):
            normalized_identifier = '256' + normalized_identifier

        if normalized_identifier:
            for candidate in Patient.objects.filter(is_active=True).only('id', 'phone'):
                candidate_phone = ''.join(ch for ch in (candidate.phone or '') if ch.isdigit())
                if candidate_phone.startswith('0') and len(candidate_phone) == 10:
                    candidate_phone = '256' + candidate_phone[1:]
                elif len(candidate_phone) == 9 and candidate_phone.startswith('7'):
                    candidate_phone = '256' + candidate_phone
                if candidate_phone == normalized_identifier:
                    patient = candidate
                    break
        
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
            messages.error(request, 'Invalid credentials. Please check and try again.')
            return render(request, 'patient_portal/login.html')
        
        # Check if locked
        if portal_access.is_locked():
            messages.error(request, 'Invalid credentials. Please try again later.')
            return render(request, 'patient_portal/login.html')
        
        # Check if active
        if not portal_access.is_active:
            messages.error(request, 'Invalid credentials. Please check and try again.')
            return render(request, 'patient_portal/login.html')
        
        # PINs are stored as SHA-256 hashes.
        supplied_hash = hashlib.sha256(pin.encode('utf-8')).hexdigest()
        if constant_time_compare(portal_access.portal_pin or '', supplied_hash):
            # Success - reset attempts
            portal_access.reset_login_attempts()
            portal_access.last_login = timezone.now()
            portal_access.save()
            
            # Rotate the session key after authentication to prevent session fixation.
            request.session.cycle_key()
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
    """Patient dashboard: only this patient's own records are queried."""
    patient_id = request.session.get('patient_portal_patient_id')
    patient = get_object_or_404(Patient, pk=patient_id, is_active=True)

    sync_upcoming_appointment_reminders(patient)

    today = timezone.localdate()
    total_appointments = patient.appointment_set.count()
    upcoming_appointments = patient.appointment_set.filter(
        appointment_date__gte=today,
        status__in=['scheduled', 'checked_in'],
    ).count()
    total_invoices = patient.invoices.count()
    total_paid = Payment.objects.filter(invoice__patient=patient, status='completed').aggregate(
        total=Sum('amount')
    )['total'] or 0
    total_balance = get_patient_outstanding_balance(patient)

    recent_appointments = patient.appointment_set.select_related('doctor', 'service').order_by(
        '-appointment_date', '-appointment_time'
    )[:5]
    upcoming_appts = patient.appointment_set.select_related('doctor', 'service').filter(
        appointment_date__gte=today,
        status__in=['scheduled', 'checked_in'],
    ).order_by('appointment_date', 'appointment_time')[:5]
    notifications = patient.portal_notifications.all()[:5]
    unread_notifications = patient.portal_notifications.filter(is_read=False).count()
    offers = [o for o in PortalOffer.objects.filter(is_published=True).order_by('-created_at')[:8] if o.is_current][:3]
    conversations = patient.portal_conversations.order_by('-updated_at')[:3]
    unread_messages = PatientMessage.objects.filter(
        conversation__patient=patient, sender_type='staff', read_at__isnull=True
    ).count()

    context = {
        'patient': patient,
        'total_appointments': total_appointments,
        'upcoming_appointments': upcoming_appointments,
        'total_invoices': total_invoices,
        'total_paid': total_paid,
        'total_balance': total_balance,
        'recent_appointments': recent_appointments,
        'upcoming_appts': upcoming_appts,
        'notifications': notifications,
        'unread_notifications': unread_notifications,
        'offers': offers,
        'conversations': conversations,
        'unread_messages': unread_messages,
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
    
    today = timezone.localdate()
    selected_date = request.GET.get('date', '').strip()
    show_all = request.GET.get('all') == '1'

    invoices = patient.invoices.all().order_by('-issue_date', '-id')
    if selected_date:
        try:
            selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            selected_date_obj = today
    else:
        selected_date_obj = today

    # Today's invoices are the default view. Patients can explicitly choose
    # another date or select "All" when they need their full history.
    if show_all:
        filtered_invoices = invoices
        filter_label = 'All invoices'
    else:
        filtered_invoices = invoices.filter(issue_date=selected_date_obj)
        filter_label = selected_date_obj.strftime('%B %d, %Y')
    
    total_amount = filtered_invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_paid = filtered_invoices.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    total_balance = get_patient_outstanding_balance(patient)
    
    log_patient_action(patient, 'Viewed Invoices', request)
    
    context = {
        'patient': patient,
        'invoices': filtered_invoices,
        'today': today,
        'selected_date': selected_date_obj,
        'show_all': show_all,
        'filter_label': filter_label,
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
def treatment_history(request):
    patient = get_object_or_404(
        Patient, pk=request.session.get('patient_portal_patient_id'), is_active=True
    )
    treatments = Treatment.objects.filter(patient=patient).select_related('doctor', 'service', 'appointment').order_by('-treatment_date', '-id')
    completed_appointments = patient.appointment_set.filter(status='completed').select_related('doctor', 'service').order_by('-appointment_date', '-appointment_time')
    log_patient_action(patient, 'Viewed Treatment History', request)
    return render(request, 'patient_portal/treatment_history.html', {
        'patient': patient, 'treatments': treatments, 'completed_appointments': completed_appointments,
    })


@patient_portal_required
def payments(request):
    """Read-only payment history for the logged-in patient only."""
    patient = get_object_or_404(
        Patient, pk=request.session.get('patient_portal_patient_id'), is_active=True
    )
    payments_qs = Payment.objects.filter(
        invoice__patient=patient, status='completed'
    ).select_related('invoice').order_by('-payment_date', '-id')
    log_patient_action(patient, 'Viewed Payments', request)
    return render(request, 'patient_portal/payments.html', {
        'patient': patient,
        'payments': payments_qs,
        'total_paid': payments_qs.aggregate(total=Sum('amount'))['total'] or 0,
        'total_balance': get_patient_outstanding_balance(patient),
    })


@patient_portal_required
def offers(request):
    patient = get_object_or_404(
        Patient, pk=request.session.get('patient_portal_patient_id'), is_active=True
    )
    today = timezone.localdate()
    offers_qs = PortalOffer.objects.filter(is_published=True).filter(
        Q(valid_from__isnull=True) | Q(valid_from__lte=today),
        Q(valid_until__isnull=True) | Q(valid_until__gte=today),
    ).order_by('-created_at')
    log_patient_action(patient, 'Viewed Offers', request)
    return render(request, 'patient_portal/offers.html', {'patient': patient, 'offers': offers_qs})


@patient_portal_required
def notifications(request):
    patient = get_object_or_404(
        Patient, pk=request.session.get('patient_portal_patient_id'), is_active=True
    )
    sync_upcoming_appointment_reminders(patient)
    notifications_qs = patient.portal_notifications.select_related('appointment', 'conversation').all()
    log_patient_action(patient, 'Viewed Notifications', request)
    return render(request, 'patient_portal/notifications.html', {
        'patient': patient,
        'notifications': notifications_qs,
        'unread_count': notifications_qs.filter(is_read=False).count(),
    })


@patient_portal_required
def notification_read(request, pk):
    patient = get_object_or_404(
        Patient, pk=request.session.get('patient_portal_patient_id'), is_active=True
    )
    notification = get_object_or_404(PortalNotification, pk=pk, patient=patient)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    if notification.url:
        return redirect(notification.url)
    return redirect('patient_portal:notifications')


@patient_portal_required
def notifications_mark_all_read(request):
    patient = get_object_or_404(
        Patient, pk=request.session.get('patient_portal_patient_id'), is_active=True
    )
    patient.portal_notifications.filter(is_read=False).update(is_read=True)
    return redirect('patient_portal:notifications')


@patient_portal_required
def messages_list(request):
    patient = get_object_or_404(
        Patient, pk=request.session.get('patient_portal_patient_id'), is_active=True
    )
    conversations = patient.portal_conversations.select_related('doctor').prefetch_related('messages').all()
    unread = PatientMessage.objects.filter(
        conversation__patient=patient, sender_type='staff', read_at__isnull=True
    ).count()
    return render(request, 'patient_portal/messages.html', {
        'patient': patient, 'conversations': conversations, 'unread_messages': unread,
    })


@patient_portal_required
def message_new(request):
    patient = get_object_or_404(
        Patient, pk=request.session.get('patient_portal_patient_id'), is_active=True
    )
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip() or 'General enquiry'
        body = request.POST.get('body', '').strip()
        if not body:
            messages.error(request, 'Please enter your message.')
            return render(request, 'patient_portal/message_new.html', {'patient': patient})
        doctor = patient.appointment_set.select_related('doctor').order_by('-appointment_date', '-appointment_time').first()
        conversation = PatientConversation.objects.create(
            patient=patient, doctor=doctor.doctor if doctor else None, subject=subject
        )
        PatientMessage.objects.create(conversation=conversation, sender_type='patient', body=body)
        _notify_patient_message_staff(conversation, 'New patient portal message')
        log_patient_action(patient, 'Started Conversation', request)
        messages.success(request, 'Your message has been sent to the clinic.')
        return redirect('patient_portal:conversation', pk=conversation.pk)
    return render(request, 'patient_portal/message_new.html', {'patient': patient})


@patient_portal_required
def conversation(request, pk):
    patient = get_object_or_404(
        Patient, pk=request.session.get('patient_portal_patient_id'), is_active=True
    )
    conversation_obj = get_object_or_404(
        PatientConversation.objects.select_related('doctor'), pk=pk, patient=patient
    )
    if request.method == 'POST':
        if conversation_obj.status == 'closed':
            messages.error(request, 'This conversation is closed. Start a new message to contact the clinic.')
            return redirect('patient_portal:conversation', pk=pk)
        body = request.POST.get('body', '').strip()
        if not body:
            messages.error(request, 'Please enter a message.')
        else:
            PatientMessage.objects.create(conversation=conversation_obj, sender_type='patient', body=body)
            _notify_patient_message_staff(conversation_obj, 'Patient replied to portal message')
            conversation_obj.save(update_fields=['updated_at'])
            messages.success(request, 'Message sent.')
            return redirect('patient_portal:conversation', pk=pk)
    PatientMessage.objects.filter(
        conversation=conversation_obj, sender_type='staff', read_at__isnull=True
    ).update(read_at=timezone.now())
    return render(request, 'patient_portal/conversation.html', {
        'patient': patient, 'conversation': conversation_obj,
        'conversation_messages': conversation_obj.messages.select_related('sender').all(),
    })


# ====================
# STAFF PATIENT MESSAGING
# ====================

def _staff_message_access(request):
    """Return True for staff allowed to manage patient portal messages."""
    user = request.user
    if not user.is_authenticated or not hasattr(user, 'profile'):
        return False
    return user.profile.has_any_role(['admin', 'receptionist', 'doctor'])


def _staff_message_queryset(request):
    """Admins/receptionists see every patient conversation; doctors see assigned conversations."""
    qs = PatientConversation.objects.select_related('patient', 'doctor').prefetch_related('messages')
    if request.user.profile.has_any_role(['admin', 'receptionist']):
        return qs
    doctor = getattr(request.user.profile, 'doctor', None)
    if doctor:
        return qs.filter(doctor=doctor)
    return qs.none()


def _notify_patient_message_staff(conversation, title='New patient portal message'):
    """Notify admin/reception staff in the existing clinic notification center."""
    from notifications.services import create_user_notification
    recipients = User.objects.filter(
        is_active=True,
        profile__role__in=['admin', 'receptionist'],
    ).distinct()
    for recipient in recipients:
        create_user_notification(
            recipient=recipient,
            notification_type='system',
            title=title,
            message=f'{conversation.patient.full_name} sent a message: {conversation.subject}',
            url=f'/portal/staff/messages/{conversation.pk}/',
            patient=conversation.patient,
            send_push=True,
        )


@login_required
def staff_messages(request):
    """Staff inbox for all patient portal conversations."""
    if not _staff_message_access(request):
        messages.error(request, 'You do not have permission to manage patient portal messages.')
        return redirect('core:dashboard')

    conversations = _staff_message_queryset(request)
    search = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    unread_only = request.GET.get('unread') == '1'

    if search:
        conversations = conversations.filter(
            Q(patient__first_name__icontains=search)
            | Q(patient__last_name__icontains=search)
            | Q(patient__phone__icontains=search)
            | Q(subject__icontains=search)
        )
    if status in ('open', 'closed'):
        conversations = conversations.filter(status=status)
    if unread_only:
        conversations = conversations.filter(messages__sender_type='patient', messages__read_at__isnull=True).distinct()

    unread_total = PatientMessage.objects.filter(
        conversation__in=_staff_message_queryset(request),
        sender_type='patient', read_at__isnull=True,
    ).count()

    rows = []
    for conversation in conversations.order_by('-updated_at')[:200]:
        unread = conversation.messages.filter(sender_type='patient', read_at__isnull=True).count()
        latest = conversation.messages.order_by('-created_at').first()
        rows.append((conversation, unread, latest))

    return render(request, 'patient_portal/staff_messages.html', {
        'conversations': rows,
        'search': search,
        'status': status,
        'unread_only': unread_only,
        'unread_total': unread_total,
    })


@login_required
def staff_conversation(request, pk):
    """Staff conversation view with reply/close/reopen controls."""
    if not _staff_message_access(request):
        messages.error(request, 'You do not have permission to manage patient portal messages.')
        return redirect('core:dashboard')

    conversation_obj = get_object_or_404(_staff_message_queryset(request), pk=pk)

    # Opening a conversation means staff has seen the patient's messages.
    conversation_obj.messages.filter(sender_type='patient', read_at__isnull=True).update(read_at=timezone.now())

    if request.method == 'POST':
        action = request.POST.get('action', 'reply')
        if action == 'close':
            conversation_obj.status = 'closed'
            conversation_obj.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'Conversation closed.')
            return redirect('patient_portal:staff_conversation', pk=pk)
        if action == 'reopen':
            conversation_obj.status = 'open'
            conversation_obj.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'Conversation reopened.')
            return redirect('patient_portal:staff_conversation', pk=pk)

        body = request.POST.get('body', '').strip()
        if not body:
            messages.error(request, 'Please enter a reply.')
        elif conversation_obj.status == 'closed':
            messages.error(request, 'This conversation is closed. Reopen it before replying.')
        else:
            PatientMessage.objects.create(
                conversation=conversation_obj,
                sender_type='staff',
                sender=request.user,
                body=body,
            )
            conversation_obj.save(update_fields=['updated_at'])
            messages.success(request, 'Reply sent to the patient.')
            return redirect('patient_portal:staff_conversation', pk=pk)

    return render(request, 'patient_portal/staff_conversation.html', {
        'conversation': conversation_obj,
        'conversation_messages': conversation_obj.messages.select_related('sender').all(),
    })


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