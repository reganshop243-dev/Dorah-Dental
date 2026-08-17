from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from datetime import date, datetime
from .models import Patient, DentalImage
from appointments.models import Appointment, Treatment
from billing.models import Invoice
from patient_portal.models import PatientPortalAccess  # ✅ ADD THIS IMPORT
import random  # ✅ ADD THIS IMPORT
from appointments.models import DentalChart

# ====================
# HELPER: Check if user is doctor
# ====================

def is_doctor(user):
    """Check if user has doctor role"""
    return hasattr(user, 'profile') and user.profile.role == 'doctor'

def get_doctor_patients(doctor):
    """Get patients assigned to a specific doctor"""
    if doctor:
        return Patient.objects.filter(
            is_active=True,
            appointment__doctor=doctor
        ).distinct()
    return Patient.objects.none()


# ====================
# PATIENT LIST
# ====================
@login_required
def patient_list(request):
    """Display all active patients with balances"""
    user_profile = request.user.profile
    
    # ✅ If doctor, only show assigned patients
    if user_profile.role == 'doctor':
        doctor = user_profile.doctor
        patients = get_doctor_patients(doctor)
        is_doctor_user = True
    else:
        patients = Patient.objects.filter(is_active=True).order_by('-registered_at')
        is_doctor_user = False
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        patients = patients.filter(
            models.Q(first_name__icontains=search) |
            models.Q(last_name__icontains=search) |
            models.Q(phone__icontains=search) |
            models.Q(email__icontains=search)
        )
    
    # Calculate balance for each patient
    patient_list = []
    for patient in patients:
        total_balance = Invoice.objects.filter(
            patient=patient
        ).aggregate(total=Sum('balance_due'))['total'] or 0
        patient.balance = total_balance
        patient_list.append(patient)
    
    context = {
        'patients': patient_list,
        'search_query': search,
        'is_doctor': is_doctor_user,
    }
    # ✅ REMOVED THE EXTRA SPACE - now properly indented with 4 spaces
    return render(request, 'patients/list.html', context)


# ====================
# PATIENT ADD (UPDATED WITH PORTAL PIN)
# ====================

@login_required
def patient_add(request):
    """Add a new patient - Doctors are NOT allowed"""
    user_profile = request.user.profile
    
    # PREVENT doctors from adding patients
    if user_profile.role == 'doctor':
        messages.error(request, '❌ Doctors are not allowed to add patients.')
        return redirect('patients:list')
    
    # Initialize form data with default values
    form_data = {
        'first_name': '',
        'last_name': '',
        'date_of_birth': '',
        'age_years': '',
        'gender': '',
        'phone': '',
        'email': '',
        'address': '',
        'next_of_kin': '',
        'next_of_kin_contact': '',
        'under_physician': '',
        'physician_details': '',
        'allergies': '',
        'current_medications': '',
        'dental_discomfort': '',
        'discomfort_details': '',
        'previous_surgery': '',
        'surgery_details': '',
        'reason_for_visit': '',
        'last_dental_visit': '',
        'registered_at': '',
        'image_type': 'clinical',
        'image_description': '',
    }
    
    if request.method == 'POST':
        try:
            # Get all form data
            form_data = {
                'first_name': request.POST.get('first_name', '').strip(),
                'last_name': request.POST.get('last_name', '').strip(),
                'date_of_birth': request.POST.get('date_of_birth', ''),
                'age_years': request.POST.get('age_years', ''),
                'gender': request.POST.get('gender', ''),
                'phone': request.POST.get('phone', '').strip(),
                'email': request.POST.get('email', '').strip(),
                'address': request.POST.get('address', '').strip(),
                'next_of_kin': request.POST.get('next_of_kin', '').strip(),
                'next_of_kin_contact': request.POST.get('next_of_kin_contact', '').strip(),
                'under_physician': request.POST.get('under_physician', ''),
                'physician_details': request.POST.get('physician_details', '').strip(),
                'allergies': request.POST.get('allergies', '').strip(),
                'current_medications': request.POST.get('current_medications', '').strip(),
                'dental_discomfort': request.POST.get('dental_discomfort', ''),
                'discomfort_details': request.POST.get('discomfort_details', '').strip(),
                'previous_surgery': request.POST.get('previous_surgery', ''),
                'surgery_details': request.POST.get('surgery_details', '').strip(),
                'reason_for_visit': request.POST.get('reason_for_visit', '').strip(),
                'last_dental_visit': request.POST.get('last_dental_visit', ''),
                'registered_at': request.POST.get('registered_at', ''),
                'image_type': request.POST.get('image_type', 'clinical'),
                'image_description': request.POST.get('image_description', '').strip(),
            }
            
            # Validate required fields
            errors = []
            
            if not form_data['first_name']:
                errors.append('First name is required')
            if not form_data['last_name']:
                errors.append('Last name is required')
            if not form_data['gender']:
                errors.append('Gender is required')
            if not form_data['phone']:
                errors.append('Phone number is required')
            if not form_data['reason_for_visit']:
                errors.append('Reason for visit is required')
            
            # Validate date of birth OR age
            if not form_data['date_of_birth'] and not form_data['age_years']:
                errors.append('Either Date of Birth or Age in Years is required')
            
            # If there are errors, show them and re-render with data
            if errors:
                for error in errors:
                    messages.error(request, f'❌ {error}')
                return render(request, 'patients/add.html', {'form_data': form_data})
            
            # Convert age to years if provided
            age_years = None
            if form_data['age_years']:
                try:
                    age_years = int(form_data['age_years'])
                    if age_years < 0 or age_years > 150:
                        messages.error(request, 'Please enter a valid age between 0 and 150')
                        return render(request, 'patients/add.html', {'form_data': form_data})
                except ValueError:
                    messages.error(request, 'Please enter a valid number for age')
                    return render(request, 'patients/add.html', {'form_data': form_data})
            
            # Create patient
            patient = Patient.objects.create(
                first_name=form_data['first_name'],
                last_name=form_data['last_name'],
                date_of_birth=form_data['date_of_birth'] or None,
                age_years=age_years,
                gender=form_data['gender'],
                phone=form_data['phone'],
                email=form_data['email'] or None,
                address=form_data['address'] or None,
                next_of_kin=form_data['next_of_kin'] or None,
                next_of_kin_contact=form_data['next_of_kin_contact'] or None,
                under_physician=form_data['under_physician'] or None,
                physician_details=form_data['physician_details'] or None,
                allergies=form_data['allergies'] or '',
                current_medications=form_data['current_medications'] or None,
                reason_for_visit=form_data['reason_for_visit'] or None,
                dental_discomfort=form_data['dental_discomfort'] or None,
                discomfort_details=form_data['discomfort_details'] or None,
                last_dental_visit=form_data['last_dental_visit'] or None,
                is_active=True
            )
            
            # Generate Portal PIN
            portal_pin = f"{random.randint(100000, 999999)}"
            PatientPortalAccess.objects.create(
                patient=patient,
                portal_pin=portal_pin,
                is_active=True
            )
            
            # Handle backdated registration date
            if form_data['registered_at']:
                try:
                    registered_datetime = datetime.strptime(form_data['registered_at'], '%Y-%m-%d')
                    patient.registered_at = registered_datetime
                    patient.save()
                except ValueError:
                    pass
            
            # Handle dental images
            image_files = request.FILES.getlist('dental_images')
            if image_files:
                image_type = form_data['image_type']
                image_description = form_data['image_description']
                
                for image_file in image_files:
                    DentalImage.objects.create(
                        patient=patient,
                        image=image_file,
                        image_type=image_type,
                        description=image_description or f"Uploaded on {timezone.now().strftime('%Y-%m-%d')}",
                        uploaded_by=request.user
                    )
            
            messages.success(
                request, 
                f'✅ Patient {patient.full_name} registered successfully!\n'
                f'🔑 Portal PIN: {portal_pin}'
            )
            
            # Store PIN in session
            request.session['new_patient_pin'] = portal_pin
            request.session['new_patient_id'] = patient.id
            
            return redirect('patients:detail', pk=patient.pk)
            
        except Exception as e:
            messages.error(request, f'❌ Error adding patient: {str(e)}')
            import traceback
            traceback.print_exc()
            return render(request, 'patients/add.html', {'form_data': form_data})
    
    # GET request - empty form
    return render(request, 'patients/add.html', {'form_data': form_data})

# ====================
# PATIENT DETAIL (UPDATED WITH PORTAL PIN)
# ====================

@login_required
def patient_detail(request, pk):
    """View patient details - Doctors can only see assigned patients"""
    patient = get_object_or_404(Patient, pk=pk)
    user_profile = request.user.profile
    
    # ✅ Check if doctor has access to this patient
    if user_profile.role == 'doctor':
        doctor = user_profile.doctor
        if doctor:
            # Check if this patient is assigned to this doctor
            has_access = Appointment.objects.filter(
                patient=patient,
                doctor=doctor
            ).exists()
            
            if not has_access:
                messages.error(request, '❌ You do not have access to this patient.')
                return redirect('patients:list')
        else:
            messages.error(request, '❌ No doctor profile found.')
            return redirect('patients:list')
    
    # Get patient's appointments (latest first)
    appointments = Appointment.objects.filter(
        patient=patient
    ).order_by('-appointment_date', '-appointment_time')
    
    # Get patient's treatments (latest first)
    treatments = Treatment.objects.filter(
        patient=patient
    ).order_by('-treatment_date')
    
    # Get patient's invoices
    invoices = Invoice.objects.filter(
        patient=patient
    ).order_by('-issue_date')
    
    # Calculate total amount
    total_amount = invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # ✅ Get portal PIN if exists
    try:
        portal_access = patient.portal_access
        portal_pin = portal_access.portal_pin
    except PatientPortalAccess.DoesNotExist:
        portal_pin = None
    
    # ✅ Get new patient PIN from session (if just created)
    new_patient_pin = request.session.pop('new_patient_pin', None)
    new_patient_id = request.session.pop('new_patient_id', None)
    
    context = {
        'patient': patient,
        'appointments': appointments,
        'treatments': treatments,
        'invoices': invoices,
        'total_amount': total_amount,
        'is_doctor': user_profile.role == 'doctor',
        'portal_pin': portal_pin,  # ✅ Pass portal PIN
        'new_patient_pin': new_patient_pin,  # ✅ Pass new patient PIN
        'new_patient_id': new_patient_id,  # ✅ Pass new patient ID
    }
    return render(request, 'patients/detail.html', context)


# ====================
# PATIENT EDIT
# ====================

@login_required
def patient_edit(request, pk):
    """Edit patient information - Doctors are NOT allowed"""
    user_profile = request.user.profile
    
    # ✅ PREVENT doctors from editing patients
    if user_profile.role == 'doctor':
        messages.error(request, '❌ Doctors are not allowed to edit patients.')
        return redirect('patients:list')
    
    patient = get_object_or_404(Patient, pk=pk)
    
    if request.method == 'POST':
        try:
            # Update fields
            patient.first_name = request.POST.get('first_name', '').strip()
            patient.last_name = request.POST.get('last_name', '').strip()
            patient.phone = request.POST.get('phone', '').strip()
            patient.email = request.POST.get('email', '').strip()
            patient.address = request.POST.get('address', '').strip()
            patient.date_of_birth = request.POST.get('date_of_birth') or None
            
            # Update age years
            age_years = request.POST.get('age_years', '')
            if age_years:
                patient.age_years = int(age_years)
            else:
                patient.age_years = None
            
            patient.gender = request.POST.get('gender')
            patient.medical_history = request.POST.get('medical_history', '').strip()
            patient.allergies = request.POST.get('allergies', '').strip()
            
            # Update backdated registration date
            registered_at = request.POST.get('registered_at', '')
            if registered_at:
                try:
                    patient.registered_at = datetime.strptime(registered_at, '%Y-%m-%d')
                except ValueError:
                    pass
            
            # Update profile picture if uploaded
            if request.FILES.get('profile_picture'):
                if patient.profile_picture:
                    patient.profile_picture.delete()
                patient.profile_picture = request.FILES.get('profile_picture')
            
            patient.save()
            
            messages.success(request, f'Patient {patient.full_name} updated successfully!')
            return redirect('patients:detail', pk=patient.pk)
            
        except Exception as e:
            messages.error(request, f'Error updating patient: {str(e)}')
            return render(request, 'patients/edit.html', {'patient': patient})
    
    context = {
        'patient': patient,
    }
    return render(request, 'patients/edit.html', context)


# ====================
# PATIENT DELETE (Archive)
# ====================

@login_required
def patient_delete(request, pk):
    """Archive/delete patient - Doctors are NOT allowed"""
    user_profile = request.user.profile
    
    # ✅ PREVENT doctors from deleting patients
    if user_profile.role == 'doctor':
        messages.error(request, '❌ Doctors are not allowed to delete patients.')
        return redirect('patients:list')
    
    patient = get_object_or_404(Patient, pk=pk)
    
    if request.method == 'POST':
        try:
            patient.is_active = False
            patient.save()
            messages.success(request, f'Patient {patient.full_name} archived successfully!')
            return redirect('patients:list')
        except Exception as e:
            messages.error(request, f'Error archiving patient: {str(e)}')
    
    context = {
        'patient': patient,
    }
    return render(request, 'patients/delete.html', context)


# ====================
# PATIENT ADD IMAGE
# ====================

@login_required
def patient_add_image(request, pk):
    """Add dental images - Doctors can add images to their patients"""
    patient = get_object_or_404(Patient, pk=pk)
    user_profile = request.user.profile
    
    # ✅ Check if doctor has access to this patient
    if user_profile.role == 'doctor':
        doctor = user_profile.doctor
        if doctor:
            has_access = Appointment.objects.filter(
                patient=patient,
                doctor=doctor
            ).exists()
            if not has_access:
                messages.error(request, '❌ You do not have access to this patient.')
                return redirect('patients:list')
        else:
            messages.error(request, '❌ No doctor profile found.')
            return redirect('patients:list')
    
    if request.method == 'POST':
        try:
            image_files = request.FILES.getlist('dental_images')
            image_type = request.POST.get('image_type', 'clinical')
            image_description = request.POST.get('image_description', '')
            
            if not image_files:
                messages.error(request, 'Please select at least one image to upload')
                return redirect('patients:detail', pk=patient.pk)
            
            for image_file in image_files:
                DentalImage.objects.create(
                    patient=patient,
                    image=image_file,
                    image_type=image_type,
                    description=image_description or f"Uploaded on {timezone.now().strftime('%Y-%m-%d')}",
                    uploaded_by=request.user
                )
            
            messages.success(request, f'{len(image_files)} image(s) uploaded successfully for {patient.full_name}')
            return redirect('patients:detail', pk=patient.pk)
            
        except Exception as e:
            messages.error(request, f'Error uploading images: {str(e)}')
    
    return render(request, 'patients/add_image.html', {'patient': patient})


# ====================
# GENERATE PORTAL PIN FOR EXISTING PATIENT
# ====================

@login_required
def generate_portal_pin(request, pk):
    """Generate portal PIN for existing patient"""
    # ✅ Only admin and receptionist can generate PINs
    if request.user.profile.role not in ['admin', 'receptionist']:
        messages.error(request, '❌ Access denied. Only admin or receptionist can generate portal PINs.')
        return redirect('patients:detail', pk=pk)
    
    patient = get_object_or_404(Patient, pk=pk)
    
    portal_pin = f"{random.randint(100000, 999999)}"
    
    portal_access, created = PatientPortalAccess.objects.get_or_create(
        patient=patient,
        defaults={
            'portal_pin': portal_pin,
            'is_active': True
        }
    )
    
    if not created:
        portal_access.portal_pin = portal_pin
        portal_access.is_active = True
        portal_access.login_attempts = 0
        portal_access.locked_until = None
        portal_access.save()
        messages.success(request, f'✅ Portal PIN updated for {patient.full_name}. New PIN: {portal_pin}')
    else:
        messages.success(request, f'✅ Portal access created for {patient.full_name}. PIN: {portal_pin}')
    
    return redirect('patients:detail', pk=pk)


# ====================
# PATIENT SEARCH (API)
# ====================

@login_required
def patient_search_api(request):
    """API endpoint for searching patients - Doctors only see their patients"""
    try:
        query = request.GET.get('q', '').strip()
        balance_filter = request.GET.get('balance', '')
        sort = request.GET.get('sort', '-registered_at')
        user_profile = request.user.profile
        
        # ✅ If doctor, only show assigned patients
        if user_profile.role == 'doctor':
            doctor = user_profile.doctor
            if doctor:
                patients = Patient.objects.filter(
                    is_active=True,
                    appointment__doctor=doctor
                ).distinct()
            else:
                patients = Patient.objects.none()
        else:
            patients = Patient.objects.filter(is_active=True)
        
        # Search - if query is provided
        if query:
            patients = patients.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(phone__icontains=query) |
                Q(email__icontains=query)
            )
        
        # Apply sorting
        if sort:
            if sort == 'first_name':
                patients = patients.order_by('first_name', 'last_name')
            elif sort == '-first_name':
                patients = patients.order_by('-first_name', '-last_name')
            else:
                patients = patients.order_by(sort)
        
        # Limit results
        patients = patients[:50]
        
        # Build results with all required fields
        results = []
        for patient in patients:
            # Calculate total balance
            total_balance = Invoice.objects.filter(
                patient=patient
            ).aggregate(total=Sum('balance_due'))['total'] or 0
            
            # Apply balance filter
            if balance_filter == 'has_balance' and total_balance <= 0:
                continue
            if balance_filter == 'no_balance' and total_balance > 0:
                continue
            
            # Calculate age
            age = None
            if patient.date_of_birth:
                today = date.today()
                age = today.year - patient.date_of_birth.year
                if (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day):
                    age -= 1
            elif patient.age_years is not None:
                age = patient.age_years
            
            # ✅ Get portal PIN
            try:
                portal_pin = patient.portal_access.portal_pin
            except PatientPortalAccess.DoesNotExist:
                portal_pin = None
            
            results.append({
                'id': patient.id,
                'full_name': patient.full_name,
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'phone': patient.phone,
                'email': patient.email or '',
                'date_of_birth': patient.date_of_birth.strftime('%b %d, %Y') if patient.date_of_birth else 'N/A',
                'age': age if age is not None else 'N/A',
                'registered_at': patient.registered_at.strftime('%b %d, %Y'),
                'balance': float(total_balance),
                'gender': patient.get_gender_display(),
                'portal_pin': portal_pin,  # ✅ Include portal PIN
            })
        
        return JsonResponse({'results': results})
        
    except Exception as e:
        print(f"Search API Error: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'results': [], 'error': str(e)}, status=500)


@login_required
def dental_chart(request, pk):
    """View and edit patient's dental chart"""
    from appointments.models import DentalChart
    from django.contrib.auth.models import User
    
    patient = get_object_or_404(Patient, pk=pk)
    user_profile = request.user.profile
    
    # Check if doctor has access
    if user_profile.role == 'doctor':
        doctor = user_profile.doctor
        if doctor:
            has_access = Appointment.objects.filter(
                patient=patient,
                doctor=doctor
            ).exists()
            if not has_access:
                messages.error(request, '❌ You do not have access to this patient.')
                return redirect('patients:list')
    
    # Get existing chart records
    chart_records = DentalChart.objects.filter(patient=patient)
    
    # Create a map of tooth records
    tooth_map = {record.tooth_number: record for record in chart_records}
    
    # Build tooth data list
    all_tooth_numbers = [16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 32, 31, 30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 20, 19, 18, 17]
    tooth_data = []
    for num in all_tooth_numbers:
        record = tooth_map.get(num)
        tooth_data.append({
            'number': num,
            'has_record': bool(record),
            'condition_display': record.get_condition_display() if record else None,
        })
    
    if request.method == 'POST':
        try:
            tooth_number = request.POST.get('tooth_number')
            condition = request.POST.get('condition')
            surface = request.POST.get('surface')
            notes = request.POST.get('notes', '')
            
            if not tooth_number or not condition:
                messages.error(request, 'Tooth number and condition are required.')
                return redirect('patients:dental_chart', pk=patient.pk)
            
            # Update or create record
            record, created = DentalChart.objects.update_or_create(
                patient=patient,
                tooth_number=int(tooth_number),
                defaults={
                    'tooth_name': get_tooth_name(int(tooth_number)),
                    'condition': condition,
                    'surface': surface if surface else None,
                    'notes': notes,
                    'created_by': request.user
                }
            )
            
            if created:
                messages.success(request, f'✅ Tooth #{tooth_number} recorded as {record.get_condition_display()}!')
            else:
                messages.success(request, f'✅ Tooth #{tooth_number} updated to {record.get_condition_display()}!')
            
            return redirect('patients:dental_chart', pk=patient.pk)
            
        except Exception as e:
            messages.error(request, f'❌ Error updating dental chart: {str(e)}')
    
    context = {
        'patient': patient,
        'tooth_data': tooth_data,
        'tooth_map': tooth_map,
        'is_doctor': user_profile.role == 'doctor',
        'condition_choices': DentalChart.TOOTH_CONDITION_CHOICES,
        'surface_choices': DentalChart.SURFACE_CHOICES,
        'tooth_numbers_upper': [16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26],
        'tooth_numbers_lower': [32, 31, 30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 20, 19, 18, 17],
    }
    return render(request, 'patients/dental_chart.html', context)


def get_tooth_name(tooth_number):
    """Get the name of a tooth based on universal numbering"""
    tooth_names = {
        1: 'Right Maxillary 3rd Molar', 2: 'Right Maxillary 2nd Molar',
        3: 'Right Maxillary 1st Molar', 4: 'Right Maxillary 2nd Premolar',
        5: 'Right Maxillary 1st Premolar', 6: 'Right Maxillary Canine',
        7: 'Right Maxillary Lateral Incisor', 8: 'Right Maxillary Central Incisor',
        9: 'Left Maxillary Central Incisor', 10: 'Left Maxillary Lateral Incisor',
        11: 'Left Maxillary Canine', 12: 'Left Maxillary 1st Premolar',
        13: 'Left Maxillary 2nd Premolar', 14: 'Left Maxillary 1st Molar',
        15: 'Left Maxillary 2nd Molar', 16: 'Left Maxillary 3rd Molar',
        17: 'Left Mandibular 3rd Molar', 18: 'Left Mandibular 2nd Molar',
        19: 'Left Mandibular 1st Molar', 20: 'Left Mandibular 2nd Premolar',
        21: 'Left Mandibular 1st Premolar', 22: 'Left Mandibular Canine',
        23: 'Left Mandibular Lateral Incisor', 24: 'Left Mandibular Central Incisor',
        25: 'Right Mandibular Central Incisor', 26: 'Right Mandibular Lateral Incisor',
        27: 'Right Mandibular Canine', 28: 'Right Mandibular 1st Premolar',
        29: 'Right Mandibular 2nd Premolar', 30: 'Right Mandibular 1st Molar',
        31: 'Right Mandibular 2nd Molar', 32: 'Right Mandibular 3rd Molar'
    }
    return tooth_names.get(tooth_number, f'Tooth #{tooth_number}')