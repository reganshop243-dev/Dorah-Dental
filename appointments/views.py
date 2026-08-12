from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
from datetime import datetime, timedelta
from .models import Appointment, Doctor, Service, Treatment
from patients.models import Patient
from billing.models import Invoice


# ====================
# HELPER: Check if user is doctor
# ====================

def is_doctor(user):
    """Check if user has doctor role"""
    return hasattr(user, 'profile') and user.profile.role == 'doctor'

def get_doctor_queryset(user, model, filter_field='doctor'):
    """Get queryset filtered for doctor if user is a doctor"""
    if is_doctor(user):
        doctor = user.profile.doctor
        if doctor:
            if filter_field == 'doctor':
                return model.objects.filter(doctor=doctor)
            elif filter_field == 'patient':
                return model.objects.filter(patient__appointment__doctor=doctor).distinct()
        return model.objects.none()
    return model.objects.all()


# ====================
# DASHBOARD VIEW
# ====================

@login_required
def dashboard(request):
    """Main dashboard view"""
    user_profile = request.user.profile
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    
    # ✅ If doctor, show only their data
    if is_doctor(request.user):
        doctor = user_profile.doctor
        if doctor:
            # Patients assigned to this doctor
            total_patients = Patient.objects.filter(
                appointment__doctor=doctor
            ).distinct().count()
            
            # Appointments for this doctor
            total_appointments_today = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=today
            ).count()
            
            total_appointments_month = Appointment.objects.filter(
                doctor=doctor,
                appointment_date__gte=start_of_month
            ).count()
            
            # Today's appointments for this doctor
            today_appointments = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=today
            ).select_related('patient', 'doctor', 'service').order_by('appointment_time')
            
            # Upcoming appointments for this doctor
            upcoming_appointments = Appointment.objects.filter(
                doctor=doctor,
                appointment_date__gte=today,
                status__in=['scheduled', 'checked_in']
            ).select_related('patient', 'doctor', 'service').order_by('appointment_date', 'appointment_time')[:10]
            
            # Recent patients assigned to this doctor
            recent_patients = Patient.objects.filter(
                appointment__doctor=doctor
            ).distinct().order_by('-registered_at')[:5]
        else:
            total_patients = 0
            total_appointments_today = 0
            total_appointments_month = 0
            today_appointments = []
            upcoming_appointments = []
            recent_patients = []
    else:
        # Admin/Receptionist/Accountant see all data
        total_patients = Patient.objects.filter(is_active=True).count()
        total_appointments_today = Appointment.objects.filter(appointment_date=today).count()
        total_appointments_month = Appointment.objects.filter(appointment_date__gte=start_of_month).count()
        
        today_appointments = Appointment.objects.filter(
            appointment_date=today
        ).select_related('patient', 'doctor', 'service').order_by('appointment_time')
        
        upcoming_appointments = Appointment.objects.filter(
            appointment_date__gte=today,
            status__in=['scheduled', 'checked_in']
        ).select_related('patient', 'doctor', 'service').order_by('appointment_date', 'appointment_time')[:10]
        
        recent_patients = Patient.objects.filter(is_active=True).order_by('-registered_at')[:5]
    
    context = {
        'total_patients': total_patients,
        'total_appointments_today': total_appointments_today,
        'total_appointments_month': total_appointments_month,
        'today_appointments': today_appointments,
        'upcoming_appointments': upcoming_appointments,
        'recent_patients': recent_patients,
        'today': today,
        'is_doctor': is_doctor(request.user),
    }
    return render(request, 'appointments/dashboard.html', context)


# ====================
# APPOINTMENT VIEWS
# ====================

@login_required
def appointment_list(request):
    """List all appointments with filters"""
    user_profile = request.user.profile
    
    # ✅ If doctor, only show their appointments
    if is_doctor(request.user):
        doctor = user_profile.doctor
        if doctor:
            appointments = Appointment.objects.filter(
                doctor=doctor
            ).select_related('patient', 'doctor', 'service').order_by('-appointment_date', '-appointment_time')
        else:
            appointments = Appointment.objects.none()
    else:
        appointments = Appointment.objects.all().select_related('patient', 'doctor', 'service').order_by('-appointment_date', '-appointment_time')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    
    # Filter by date
    date_filter = request.GET.get('date', '')
    if date_filter:
        appointments = appointments.filter(appointment_date=date_filter)
    
    context = {
        'appointments': appointments,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'status_choices': Appointment.STATUS_CHOICES,
        'is_doctor': is_doctor(request.user),
    }
    return render(request, 'appointments/appointment_list.html', context)


@login_required
def appointment_add(request):
    """Add a new appointment"""
    user_profile = request.user.profile
    
    # ✅ Doctors can only add appointments for their patients
    if request.method == 'POST':
        try:
            patient_id = request.POST.get('patient')
            doctor_id = request.POST.get('doctor')
            service_id = request.POST.get('service')
            appointment_date = request.POST.get('appointment_date')
            appointment_time = request.POST.get('appointment_time')
            notes = request.POST.get('notes', '')
            
            # Get notification fields
            notification_email = request.POST.get('notification_email', '').strip()
            notification_phone = request.POST.get('notification_phone', '').strip()
            send_reminder = request.POST.get('send_reminder') == 'on'
            
            # Get treatment fields
            diagnosis = request.POST.get('diagnosis', '')
            consultation_notes = request.POST.get('consultation_notes', '')
            treatment_plan = request.POST.get('treatment_plan', '')
            prescription = request.POST.get('prescription', '')
            treatment_cost = request.POST.get('treatment_cost') or None
            referred_to = request.POST.get('referred_to', '')
            follow_up_date = request.POST.get('follow_up_date') or None
            follow_up_notes = request.POST.get('follow_up_notes', '')
            
            patient = get_object_or_404(Patient, pk=patient_id)
            
            # ✅ If user is doctor, force doctor_id to their own ID
            if is_doctor(request.user):
                doctor = user_profile.doctor
                if not doctor:
                    messages.error(request, '❌ No doctor profile found.')
                    return redirect('appointments:list')
                doctor_id = doctor.id
                
                # ✅ Check if patient is assigned to this doctor
                has_access = Appointment.objects.filter(
                    patient=patient,
                    doctor=doctor
                ).exists()
                
                # Allow if patient has been seen by this doctor OR is new
                if not has_access and patient.appointment_set.exists():
                    messages.error(request, '❌ This patient is not assigned to you.')
                    return redirect('appointments:list')
            
            doctor = get_object_or_404(Doctor, pk=doctor_id)
            service = get_object_or_404(Service, pk=service_id)
            
            # If notification email is not provided, use patient's email
            if not notification_email:
                notification_email = patient.email
            
            # If notification phone is not provided, use patient's phone
            if not notification_phone:
                notification_phone = patient.phone
            
            # Create the appointment
            appointment = Appointment.objects.create(
                patient=patient,
                doctor=doctor,
                service=service,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                duration_minutes=service.duration_minutes,
                notes=notes,
                notification_email=notification_email,
                notification_phone=notification_phone,
                send_reminder=send_reminder,
                # Treatment fields
                diagnosis=diagnosis,
                consultation_notes=consultation_notes,
                treatment_plan=treatment_plan,
                prescription=prescription,
                treatment_cost=treatment_cost,
                referred_to=referred_to,
                follow_up_date=follow_up_date,
                follow_up_notes=follow_up_notes,
            )
            messages.success(request, f'✅ Appointment created for {patient.full_name}')
            
            # Send confirmation SMS if send_reminder is checked
            if send_reminder:
                try:
                    from notifications.yoola_sms import YoolaSMS
                    from notifications.models import NotificationSetting
                    
                    # Convert date and time strings to datetime objects for formatting
                    appointment_date_obj = datetime.strptime(appointment_date, '%Y-%m-%d').date()
                    appointment_time_obj = datetime.strptime(appointment_time, '%H:%M').time()
                    
                    # Prepare data for the message
                    data = {
                        'patient_name': patient.full_name,
                        'appointment_date': appointment_date_obj.strftime('%A, %B %d, %Y'),
                        'appointment_time': appointment_time_obj.strftime('%I:%M %p'),
                        'doctor_name': doctor.name,
                        'service_name': service.name,
                        'clinic_phone': getattr(settings, 'BUSINESS_PHONE', '+256 700 000 000'),
                        'clinic_name': getattr(settings, 'BUSINESS_SHORT_NAME', "Dora's Dental Gem"),
                    }
                    
                    # Get notification settings
                    settings_obj = NotificationSetting.objects.first()
                    
                    # Send SMS using Yoola
                    if notification_phone:
                        yoola = YoolaSMS()
                        
                        # Create the message
                        message = f"Dora's Dental Gem: Appointment confirmed for {data['patient_name']} on {data['appointment_date']} at {data['appointment_time']} with Dr. {data['doctor_name']}. Call {data['clinic_phone']} to reschedule."
                        
                        # Send the SMS
                        result = yoola.send_sms(notification_phone, message)
                        
                        if result.get('success'):
                            messages.info(request, '✅ Appointment confirmation sent via SMS')
                        else:
                            messages.warning(request, f'⚠️ SMS not sent: {result.get("error")}')
                    
                    # Send email if email is available
                    if notification_email and settings_obj and settings_obj.channel in ['email', 'both']:
                        from django.core.mail import send_mail
                        email_subject = f"Appointment Confirmation - {data['clinic_name']}"
                        email_body = f"""
Dear {data['patient_name']},

Your appointment has been confirmed at {data['clinic_name']}.

Appointment Details:
- Date: {data['appointment_date']}
- Time: {data['appointment_time']}
- Doctor: Dr. {data['doctor_name']}
- Service: {data['service_name']}

Please arrive 15 minutes before your appointment.

If you need to reschedule, please call us at {data['clinic_phone']}.

Thank you,
{data['clinic_name']} Team
"""
                        send_mail(
                            subject=email_subject,
                            message=email_body,
                            from_email=settings.DEFAULT_FROM_EMAIL or 'noreply@dorasdentalgem.com',
                            recipient_list=[notification_email],
                            fail_silently=True,
                        )
                        messages.info(request, '✅ Appointment confirmation sent via Email')
                        
                except Exception as e:
                    # Don't fail appointment creation if notification fails
                    print(f"Notification error: {e}")
                    import traceback
                    traceback.print_exc()
                    messages.warning(request, f'⚠️ Appointment created but reminder failed: {str(e)}')
            
            return redirect('appointments:list')
        except Exception as e:
            messages.error(request, f'❌ Error creating appointment: {str(e)}')
            import traceback
            traceback.print_exc()
    
    # ✅ Get patients based on role
    if is_doctor(request.user):
        doctor = user_profile.doctor
        if doctor:
            patients = Patient.objects.filter(
                appointment__doctor=doctor
            ).distinct().order_by('first_name', 'last_name')
            doctors = Doctor.objects.filter(pk=doctor.id)
        else:
            patients = Patient.objects.none()
            doctors = Doctor.objects.none()
    else:
        patients = Patient.objects.filter(is_active=True).order_by('first_name', 'last_name')
        doctors = Doctor.objects.filter(is_active=True).order_by('name')
    
    services = Service.objects.filter(is_active=True).order_by('name')
    
    context = {
        'patients': patients,
        'doctors': doctors,
        'services': services,
        'is_doctor': is_doctor(request.user),
    }
    return render(request, 'appointments/appointment_add.html', context)


@login_required
def appointment_detail(request, pk):
    """View appointment details"""
    appointment = get_object_or_404(Appointment, pk=pk)
    user_profile = request.user.profile
    
    # ✅ Check if doctor has access to this appointment
    if is_doctor(request.user):
        doctor = user_profile.doctor
        if doctor and appointment.doctor != doctor:
            messages.error(request, '❌ You do not have access to this appointment.')
            return redirect('appointments:list')
    
    return render(request, 'appointments/appointment_detail.html', {
        'appointment': appointment,
        'is_doctor': is_doctor(request.user),
    })


@login_required
def appointment_edit(request, pk):
    """Edit an appointment"""
    appointment = get_object_or_404(Appointment, pk=pk)
    user_profile = request.user.profile
    
    # ✅ Check if doctor has access to this appointment
    if is_doctor(request.user):
        doctor = user_profile.doctor
        if doctor and appointment.doctor != doctor:
            messages.error(request, '❌ You do not have access to this appointment.')
            return redirect('appointments:list')
    
    if request.method == 'POST':
        try:
            appointment.patient_id = request.POST.get('patient')
            appointment.doctor_id = request.POST.get('doctor')
            appointment.service_id = request.POST.get('service')
            appointment.appointment_date = request.POST.get('appointment_date')
            appointment.appointment_time = request.POST.get('appointment_time')
            appointment.status = request.POST.get('status')
            appointment.notes = request.POST.get('notes', '')
            
            # Update treatment fields
            appointment.diagnosis = request.POST.get('diagnosis', '')
            appointment.consultation_notes = request.POST.get('consultation_notes', '')
            appointment.treatment_plan = request.POST.get('treatment_plan', '')
            appointment.prescription = request.POST.get('prescription', '')
            appointment.treatment_cost = request.POST.get('treatment_cost') or None
            appointment.referred_to = request.POST.get('referred_to', '')
            appointment.follow_up_date = request.POST.get('follow_up_date') or None
            appointment.follow_up_notes = request.POST.get('follow_up_notes', '')
            
            # Update notification fields
            appointment.notification_email = request.POST.get('notification_email', '').strip()
            appointment.notification_phone = request.POST.get('notification_phone', '').strip()
            appointment.send_reminder = request.POST.get('send_reminder') == 'on'
            
            # Reset reminder_sent if date/time changed or send_reminder turned on
            if appointment.send_reminder:
                appointment.reminder_sent = False
            
            appointment.save()
            
            messages.success(request, '✅ Appointment updated successfully!')
            return redirect('appointments:detail', pk=appointment.pk)
        except Exception as e:
            messages.error(request, f'❌ Error updating appointment: {str(e)}')
    
    # Get patients based on role for the form
    if is_doctor(request.user):
        doctor = user_profile.doctor
        if doctor:
            patients = Patient.objects.filter(
                appointment__doctor=doctor
            ).distinct().order_by('first_name', 'last_name')
            doctors = Doctor.objects.filter(pk=doctor.id)
        else:
            patients = Patient.objects.none()
            doctors = Doctor.objects.none()
    else:
        patients = Patient.objects.filter(is_active=True).order_by('first_name', 'last_name')
        doctors = Doctor.objects.filter(is_active=True).order_by('name')
    
    services = Service.objects.filter(is_active=True).order_by('name')
    
    context = {
        'appointment': appointment,
        'patients': patients,
        'doctors': doctors,
        'services': services,
        'is_doctor': is_doctor(request.user),
    }
    return render(request, 'appointments/appointment_edit.html', context)


@login_required
def appointment_delete(request, pk):
    """Delete an appointment"""
    appointment = get_object_or_404(Appointment, pk=pk)
    user_profile = request.user.profile
    
    # ✅ Check if doctor has access to this appointment
    if is_doctor(request.user):
        doctor = user_profile.doctor
        if doctor and appointment.doctor != doctor:
            messages.error(request, '❌ You do not have access to this appointment.')
            return redirect('appointments:list')
    
    if request.method == 'POST':
        appointment.delete()
        messages.success(request, '✅ Appointment deleted successfully!')
        return redirect('appointments:list')
    return render(request, 'appointments/appointment_delete.html', {'appointment': appointment})


@login_required
def calendar_view(request):
    """Calendar view for appointments"""
    user_profile = request.user.profile
    
    # ✅ Get appointments based on role
    if is_doctor(request.user):
        doctor = user_profile.doctor
        if doctor:
            appointments = Appointment.objects.filter(doctor=doctor)
        else:
            appointments = Appointment.objects.none()
    else:
        appointments = Appointment.objects.all()
    
    return render(request, 'appointments/calendar.html', {
        'appointments': appointments,
        'is_doctor': is_doctor(request.user),
    })


# ====================
# SERVICE VIEWS
# ====================

@login_required
def service_list(request):
    """List all services - All users can view"""
    services = Service.objects.filter(is_active=True).order_by('name')
    return render(request, 'appointments/services.html', {
        'services': services,
        'is_doctor': is_doctor(request.user),
    })


@login_required
def service_add(request):
    """Add a new service - PREVENT doctors from adding"""
    # ✅ PREVENT doctors from adding services
    if is_doctor(request.user):
        messages.error(request, '❌ Doctors are not allowed to add services.')
        return redirect('appointments:services')
    
    if request.method == 'POST':
        try:
            service = Service.objects.create(
                name=request.POST.get('name'),
                description=request.POST.get('description', ''),
                price=request.POST.get('price'),
                duration_minutes=request.POST.get('duration_minutes', 30)
            )
            messages.success(request, f'✅ Service "{service.name}" added successfully!')
            return redirect('appointments:services')
        except Exception as e:
            messages.error(request, f'❌ Error adding service: {str(e)}')
    return render(request, 'appointments/service_add.html')


@login_required
def service_edit(request, pk):
    """Edit a service - PREVENT doctors from editing"""
    # ✅ PREVENT doctors from editing services
    if is_doctor(request.user):
        messages.error(request, '❌ Doctors are not allowed to edit services.')
        return redirect('appointments:services')
    
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        try:
            service.name = request.POST.get('name')
            service.description = request.POST.get('description')
            service.price = request.POST.get('price')
            service.duration_minutes = request.POST.get('duration_minutes', 30)
            service.save()
            messages.success(request, f'✅ Service "{service.name}" updated successfully!')
            return redirect('appointments:services')
        except Exception as e:
            messages.error(request, f'❌ Error updating service: {str(e)}')
    return render(request, 'appointments/service_edit.html', {'service': service})


@login_required
def service_delete(request, pk):
    """Delete a service - PREVENT doctors from deleting"""
    # ✅ PREVENT doctors from deleting services
    if is_doctor(request.user):
        messages.error(request, '❌ Doctors are not allowed to delete services.')
        return redirect('appointments:services')
    
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        service.is_active = False
        service.save()
        messages.success(request, f'✅ Service "{service.name}" removed successfully!')
        return redirect('appointments:services')
    return render(request, 'appointments/service_delete.html', {'service': service})


# ====================
# DOCTOR VIEWS
# ====================

@login_required
def doctor_list(request):
    """List all doctors - All users can view"""
    doctors = Doctor.objects.filter(is_active=True).order_by('name')
    return render(request, 'appointments/doctors.html', {
        'doctors': doctors,
        'is_doctor': is_doctor(request.user),
    })


@login_required
def doctor_add(request):
    """Add a new doctor - PREVENT doctors from adding"""
    # ✅ PREVENT doctors from adding doctors
    if is_doctor(request.user):
        messages.error(request, '❌ Doctors are not allowed to add new doctors.')
        return redirect('appointments:doctors')
    
    if request.method == 'POST':
        try:
            # Clean name - remove any "Dr." prefixes
            import re
            name = request.POST.get('name', '').strip()
            name = re.sub(r'^Dr\.\s*', '', name, flags=re.IGNORECASE)
            name = re.sub(r'\s+Dr\.\s*', ' ', name, flags=re.IGNORECASE)
            name = ' '.join(name.split())
            
            doctor = Doctor.objects.create(
                name=name,
                specialization=request.POST.get('specialization'),
                phone=request.POST.get('phone'),
                email=request.POST.get('email')
            )
            messages.success(request, f'✅ Dr. {doctor.name} added successfully!')
            return redirect('appointments:doctors')
        except Exception as e:
            messages.error(request, f'❌ Error adding doctor: {str(e)}')
    return render(request, 'appointments/doctor_add.html')


@login_required
def doctor_edit(request, pk):
    """Edit a doctor - PREVENT doctors from editing"""
    # ✅ PREVENT doctors from editing doctors
    if is_doctor(request.user):
        messages.error(request, '❌ Doctors are not allowed to edit doctor profiles.')
        return redirect('appointments:doctors')
    
    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == 'POST':
        try:
            # Clean name - remove any "Dr." prefixes
            import re
            name = request.POST.get('name', '').strip()
            name = re.sub(r'^Dr\.\s*', '', name, flags=re.IGNORECASE)
            name = re.sub(r'\s+Dr\.\s*', ' ', name, flags=re.IGNORECASE)
            name = ' '.join(name.split())
            
            doctor.name = name
            doctor.specialization = request.POST.get('specialization')
            doctor.phone = request.POST.get('phone')
            doctor.email = request.POST.get('email')
            doctor.save()
            messages.success(request, f'✅ Dr. {doctor.name} updated successfully!')
            return redirect('appointments:doctors')
        except Exception as e:
            messages.error(request, f'❌ Error updating doctor: {str(e)}')
    return render(request, 'appointments/doctor_edit.html', {'doctor': doctor})


@login_required
def doctor_delete(request, pk):
    """Delete a doctor - PREVENT doctors from deleting"""
    # ✅ PREVENT doctors from deleting doctors
    if is_doctor(request.user):
        messages.error(request, '❌ Doctors are not allowed to delete doctors.')
        return redirect('appointments:doctors')
    
    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == 'POST':
        doctor.is_active = False
        doctor.save()
        messages.success(request, f'✅ Dr. {doctor.name} removed successfully!')
        return redirect('appointments:doctors')
    return render(request, 'appointments/doctor_delete.html', {'doctor': doctor})


# ====================
# API VIEWS
# ====================

@login_required
def services_search_api(request):
    """API endpoint for searching services"""
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    services = Service.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query)
    ).filter(is_active=True)[:20]
    
    results = []
    for service in services:
        results.append({
            'id': service.id,
            'name': service.name,
            'price': float(service.price),
        })
    
    return JsonResponse({'results': results})