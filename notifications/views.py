from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from .models import NotificationSetting, NotificationLog
from .services import NotificationService


@login_required
def notification_settings(request):
    """Configure notification settings"""
    # Only admin can access
    if request.user.profile.role != 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('core:dashboard')
    
    settings_obj = NotificationSetting.objects.first()
    if not settings_obj:
        settings_obj = NotificationSetting.objects.create()
    
    if request.method == 'POST':
        try:
            settings_obj.enable_reminders = request.POST.get('enable_reminders') == 'on'
            settings_obj.reminder_hours_before = int(request.POST.get('reminder_hours_before', 24))
            settings_obj.channel = request.POST.get('channel', 'both')
            
            # Email settings
            settings_obj.email_subject = request.POST.get('email_subject', "Appointment Reminder")
            settings_obj.email_template = request.POST.get('email_template', "")
            
            # SMS settings
            settings_obj.sms_template = request.POST.get('sms_template', "")
            
            # Twilio settings (keep for compatibility)
            settings_obj.twilio_account_sid = request.POST.get('twilio_account_sid', '')
            settings_obj.twilio_auth_token = request.POST.get('twilio_auth_token', '')
            settings_obj.twilio_phone_number = request.POST.get('twilio_phone_number', '')
            
            settings_obj.save()
            messages.success(request, 'Notification settings updated successfully!')
        except Exception as e:
            messages.error(request, f'Error updating settings: {str(e)}')
    
    # Get recent notification logs
    logs = NotificationLog.objects.all()[:20]
    
    context = {
        'settings': settings_obj,
        'logs': logs,
    }
    return render(request, 'notifications/settings.html', context)


@login_required
def send_test_reminder(request):
    """Send a test reminder to the logged-in user"""
    if request.method == 'POST':
        try:
            from .services import NotificationService
            from datetime import datetime, timedelta
            from appointments.models import Appointment, Patient, Doctor, Service
            
            test_type = request.POST.get('test_type', 'email')
            
            # Get user's email and phone
            email = request.user.email
            phone = request.user.profile.phone
            
            # Create a test appointment
            patient = Patient.objects.filter(email=email).first()
            if not patient:
                patient = Patient.objects.create(
                    first_name=request.user.first_name or 'Test',
                    last_name=request.user.last_name or 'User',
                    phone=phone or '+256700000000',
                    email=email or 'test@example.com',
                    date_of_birth=datetime.now().date() - timedelta(days=30*365),
                    gender='M'
                )
            
            doctor = Doctor.objects.first()
            if not doctor:
                doctor = Doctor.objects.create(
                    name='Dr. Test Doctor',
                    specialization='General Dentistry'
                )
            
            service = Service.objects.first()
            if not service:
                service = Service.objects.create(
                    name='Test Service',
                    price=100000
                )
            
            appointment = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                service=service,
                appointment_date=datetime.now().date() + timedelta(days=1),
                appointment_time=datetime.now().time(),
                status='scheduled'
            )
            
            service_obj = NotificationService()
            
            # Override channel based on test type
            if test_type == 'email':
                service_obj.send_email_reminder(appointment, service_obj.prepare_data(appointment))
                messages.success(request, f'✅ Test email sent to {email}! Please check your inbox.')
            elif test_type == 'sms':
                service_obj.send_sms_reminder(appointment, service_obj.prepare_data(appointment))
                messages.success(request, f'✅ Test SMS sent to {phone}! Please check your phone.')
            else:
                service_obj.send_appointment_reminder(appointment)
                messages.success(request, f'✅ Test email sent to {email} and SMS sent to {phone}!')
            
            # Delete the test appointment
            appointment.delete()
            
        except Exception as e:
            messages.error(request, f'❌ Error sending test: {str(e)}')
    
    return redirect('notifications:settings')


@login_required
def send_test_email(request):
    """Send a test email only"""
    if request.method == 'POST':
        try:
            email = request.user.email
            if not email:
                messages.error(request, 'You don\'t have an email address configured.')
                return redirect('notifications:settings')
            
            # Get the email template from settings
            settings_obj = NotificationSetting.objects.first()
            
            # Prepare test data
            from datetime import datetime, timedelta
            test_data = {
                'patient_name': request.user.get_full_name() or 'Test User',
                'appointment_date': (datetime.now() + timedelta(days=2)).strftime('%A, %B %d, %Y'),
                'appointment_time': '10:00 AM',
                'doctor_name': 'Dr. Test Doctor',
                'service_name': 'Dental Checkup',
                'clinic_name': getattr(settings, 'BUSINESS_SHORT_NAME', "Dora's Dental Gem"),
                'clinic_phone': getattr(settings, 'BUSINESS_PHONE', '+256 700 000 000'),
                'clinic_email': getattr(settings, 'BUSINESS_EMAIL', 'info@dorasdentalgem.com'),
                'clinic_address': getattr(settings, 'BUSINESS_ADDRESS', 'Kampala, Uganda'),
            }
            
            # Render the template
            from django.template import Context, Template
            template = Template(settings_obj.email_template if settings_obj else "Test appointment reminder for {{ patient_name }}")
            context = Context(test_data)
            message = template.render(context)
            
            # Send email
            send_mail(
                subject=settings_obj.email_subject if settings_obj else 'Test Appointment Reminder',
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@dorasdentalgem.com',
                recipient_list=[email],
                fail_silently=False,
            )
            
            messages.success(request, f'✅ Test email sent successfully to {email}!')
        except Exception as e:
            messages.error(request, f'❌ Error sending test email: {str(e)}')
    
    return redirect('notifications:settings')


@login_required
def send_test_sms(request):
    """Send a test SMS only"""
    if request.method == 'POST':
        try:
            from .yoola_sms import YoolaSMS
            
            phone = request.user.profile.phone
            if not phone:
                messages.error(request, 'You don\'t have a phone number configured.')
                return redirect('notifications:settings')
            
            # Get the SMS template from settings
            settings_obj = NotificationSetting.objects.first()
            
            # Prepare test data
            from datetime import datetime, timedelta
            test_data = {
                'patient_name': request.user.get_full_name() or 'Test User',
                'appointment_date': (datetime.now() + timedelta(days=2)).strftime('%A, %B %d, %Y'),
                'appointment_time': '10:00 AM',
                'doctor_name': 'Dr. Test Doctor',
                'clinic_name': getattr(settings, 'BUSINESS_SHORT_NAME', "Dora's Dental Gem"),
                'clinic_phone': getattr(settings, 'BUSINESS_PHONE', '+256 700 000 000'),
            }
            
            # Render SMS template
            from django.template import Context, Template
            template = Template(settings_obj.sms_template if settings_obj else "Test SMS: {{ patient_name }}, your appointment is on {{ appointment_date }}")
            context = Context(test_data)
            message = template.render(context)
            
            # Send SMS via Yoola
            yoola = YoolaSMS()
            result = yoola.send_sms(phone, message)
            
            if result.get('success'):
                messages.success(request, f'✅ Test SMS sent successfully to {phone}!')
            else:
                messages.error(request, f'❌ Failed to send SMS: {result.get("error")}')
                
        except Exception as e:
            messages.error(request, f'❌ Error sending test SMS: {str(e)}')
    
    return redirect('notifications:settings')


@login_required
def test_yoola_sms(request):
    """Test Yoola SMS integration"""
    if request.method == 'POST':
        try:
            from .yoola_sms import YoolaSMS
            
            phone = request.POST.get('phone_number')
            message = request.POST.get('message')
            
            if not phone:
                messages.error(request, 'Please enter a phone number')
                return redirect('notifications:settings')
            
            if not message:
                messages.error(request, 'Please enter a message')
                return redirect('notifications:settings')
            
            yoola = YoolaSMS()
            result = yoola.send_sms(phone, message)
            
            if result.get('success'):
                messages.success(request, f'✅ Test SMS sent to {phone}!')
            else:
                messages.error(request, f'❌ Failed to send SMS: {result.get("error")}')
                
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
    
    return redirect('notifications:settings')



@login_required
def send_upcoming_reminders(request):
    """Send reminders for upcoming appointments"""
    if request.user.profile.role not in ['admin', 'receptionist']:
        messages.error(request, 'Access denied. Admin or Receptionist only.')
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        days = int(request.POST.get('days', 2))
        
        from django.utils import timezone
        from datetime import timedelta
        from appointments.models import Appointment
        from .services import NotificationService
        
        today = timezone.now().date()
        target_date = today + timedelta(days=days)
        
        appointments = Appointment.objects.filter(
            appointment_date=target_date,
            status__in=['scheduled', 'checked_in'],
            send_reminder=True,
            reminder_sent=False
        )
        
        sent_count = 0
        error_count = 0
        
        for appointment in appointments:
            try:
                service = NotificationService()
                service.send_appointment_reminder(appointment)
                appointment.reminder_sent = True
                appointment.save()
                sent_count += 1
            except Exception as e:
                error_count += 1
        
        messages.success(
            request, 
            f'✅ Reminders sent: {sent_count} successful, {error_count} failed for {target_date}'
        )
        return redirect('notifications:upcoming_reminders')
    
    # GET request - show the form
    from django.utils import timezone
    from datetime import timedelta
    from appointments.models import Appointment
    
    today = timezone.now().date()
    
    # Get upcoming appointments for the next 7 days
    upcoming_appointments = Appointment.objects.filter(
        appointment_date__gte=today,
        appointment_date__lte=today + timedelta(days=7),
        status__in=['scheduled', 'checked_in']
    ).select_related('patient', 'doctor', 'service').order_by('appointment_date')
    
    # Group by date
    appointments_by_date = {}
    for appt in upcoming_appointments:
        date_str = appt.appointment_date.strftime('%Y-%m-%d')
        if date_str not in appointments_by_date:
            appointments_by_date[date_str] = []
        appointments_by_date[date_str].append(appt)
    
    context = {
        'appointments_by_date': appointments_by_date,
        'today': today,
    }
    return render(request, 'notifications/upcoming_reminders.html', context)


from django.http import JsonResponse

@login_required
def send_single_reminder(request, pk):
    """Send a single appointment reminder via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    try:
        from appointments.models import Appointment
        from .services import NotificationService
        
        appointment = Appointment.objects.get(pk=pk)
        
        # Check if already sent
        if appointment.reminder_sent:
            return JsonResponse({'success': False, 'error': 'Reminder already sent'})
        
        service = NotificationService()
        service.send_appointment_reminder(appointment)
        
        appointment.reminder_sent = True
        appointment.save()
        
        return JsonResponse({'success': True})
    except Appointment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Appointment not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})




