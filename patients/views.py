from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.db.models import Q, Sum, Value, DecimalField, Count, OuterRef, Subquery
from django.http import JsonResponse
from django.utils import timezone
from datetime import date, datetime
from .models import Patient, DentalImage, PatientContactAccessRequest
from appointments.models import Appointment, Treatment
from billing.models import Invoice
from patient_portal.models import PatientPortalAccess  # âœ… ADD THIS IMPORT
import random  # legacy compatibility
import hashlib
from appointments.models import DentalChart

# ====================
# HELPER: Check if user is doctor
# ====================

def is_doctor(user):
    """Check if user has doctor role"""
    return (
        hasattr(user, 'profile')
        and user.profile.has_role('doctor')
        and not user.profile.has_role('admin')
    )

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
    """Display active patients with server-side filtering and pagination."""
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.db.models.functions import Coalesce

    user_profile = request.user.profile

    # ---------------------------------------------------------
    # BASE PATIENT QUERY
    # ---------------------------------------------------------
    if user_profile.has_role('doctor'):
        doctor = user_profile.doctor
        patients = get_doctor_patients(doctor)
        is_doctor_user = True
    else:
        patients = Patient.objects.filter(is_active=True)
        is_doctor_user = False

    # ---------------------------------------------------------
    # FILTER VALUES
    # ---------------------------------------------------------
    search = request.GET.get('search', '').strip()
    balance_filter = request.GET.get('balance', '').strip()
    sort = request.GET.get('sort', '-registered_at').strip()

    allowed_sorts = {
        '-registered_at',
        'registered_at',
        'first_name',
        '-first_name',
        'last_name',
        '-last_name',
    }

    if sort not in allowed_sorts:
        sort = '-registered_at'

    # ---------------------------------------------------------
    # SEARCH
    # ---------------------------------------------------------
    if search:
        patients = patients.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(phone__icontains=search)
            | Q(email__icontains=search)
        )

    # ---------------------------------------------------------
    # INVOICE + BALANCE CALCULATION
    #
    # invoice_count:
    #   0 = patient has never been invoiced
    #
    # patient_balance:
    #   > 0 = money still owed
    #   0   = invoice fully paid
    #   < 0 = credit/overpayment
    # ---------------------------------------------------------
    patients = patients.annotate(
        invoice_count=Count(
            'invoices',
            distinct=True
        ),

        patient_balance=Coalesce(
            Subquery(
                Invoice.objects.filter(
                    patient=OuterRef('pk')
                ).order_by('-issue_date', '-id').values('balance_due')[:1],
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
            Value(
                0,
                output_field=DecimalField(
                    max_digits=12,
                    decimal_places=2
                )
            )
        )
    )

    # ---------------------------------------------------------
    # BALANCE FILTER
    # ---------------------------------------------------------
    if balance_filter == 'has_balance':
        patients = patients.filter(
            patient_balance__gt=0
        )

    elif balance_filter == 'no_balance':
        patients = patients.filter(
            patient_balance__lte=0
        )

    # ---------------------------------------------------------
    # SORTING
    # ---------------------------------------------------------
    patients = patients.order_by(sort)

    # ---------------------------------------------------------
    # PAGINATION
    # ---------------------------------------------------------
    paginator = Paginator(patients, 20)
    page_number = request.GET.get('page', 1)

    try:
        patients_page = paginator.page(page_number)
    except (PageNotAnInteger, EmptyPage):
        patients_page = paginator.page(1)

    # ---------------------------------------------------------
    # CONTEXT
    # ---------------------------------------------------------
    context = {
        'patients': patients_page,
        'page_obj': patients_page,
        'paginator': paginator,
        'is_paginated': patients_page.has_other_pages(),

        'total_count': paginator.count,

        'search_query': search,
        'balance_filter': balance_filter,
        'sort_filter': sort,

        'is_doctor': is_doctor_user,
    }

    return render(
        request,
        'patients/list.html',
        context
    )

# ====================
# PATIENT ADD (UPDATED WITH PORTAL PIN)
# ====================

@login_required
def patient_add(request):
    """Add a new patient - Doctors are NOT allowed"""
    user_profile = request.user.profile
    
    # PREVENT doctors from adding patients
    if user_profile.has_role('doctor'):
        messages.error(request, 'âŒ Doctors are not allowed to add patients.')
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
                    messages.error(request, f'âŒ {error}')
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
                portal_pin=hashlib.sha256(portal_pin.encode()).hexdigest(),
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
                f'âœ… Patient {patient.full_name} registered successfully!\n'
                f'ðŸ”‘ Portal PIN: {portal_pin}'
            )
            
            # Store PIN in session
            request.session['new_patient_pin'] = portal_pin
            request.session['new_patient_id'] = patient.id
            
            return redirect('patients:detail', pk=patient.pk)
            
        except Exception as e:
            messages.error(request, f'âŒ Error adding patient: {str(e)}')
            import traceback
            traceback.print_exc()
            return render(request, 'patients/add.html', {'form_data': form_data})
    
    # GET request - empty form
    return render(request, 'patients/add.html', {'form_data': form_data})

# ====================
# PATIENT DETAIL (UPDATED WITH PORTAL PIN)
# ====================

@login_required
def request_contact_access(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    profile = request.user.profile
    if not profile.has_permission('patients.contacts.request'):
        messages.error(request, 'You do not have permission to request patient contact information.')
        return redirect('patients:detail', pk=pk)
    if not is_doctor(request.user):
        messages.error(request, 'Contact access requests are for doctors who need restricted contact information.')
        return redirect('patients:detail', pk=pk)
    doctor = profile.doctor
    if not doctor or not Appointment.objects.filter(patient=patient, doctor=doctor).exists():
        messages.error(request, 'You do not have access to this patient.')
        return redirect('patients:list')
    existing = PatientContactAccessRequest.objects.filter(patient=patient, requester=request.user).order_by('-requested_at').first()
    if existing and existing.status == 'approved':
        return redirect('patients:detail', pk=pk)
    if existing and existing.status == 'pending':
        messages.info(request, 'Your contact access request is already pending administrator approval.')
        return redirect('patients:detail', pk=pk)
    access_request = PatientContactAccessRequest.objects.create(patient=patient, requester=request.user)
    from notifications.services import create_user_notification
    from django.contrib.auth.models import User
    for admin in User.objects.filter(profile__role='admin', is_active=True).distinct():
        create_user_notification(
            recipient=admin,
            notification_type='contact_access_request',
            title='Patient contact access requested',
            message=f'{request.user.get_full_name() or request.user.username} requested access to {patient.full_name} contact information.',
            url='/notifications/', patient=patient, send_push=True,
        )
    messages.success(request, 'Access request sent to an administrator.')
    return redirect('patients:detail', pk=pk)


@login_required
def patient_detail(request, pk):
    """View patient details - Doctors can only see assigned patients"""
    patient = get_object_or_404(Patient, pk=pk)
    user_profile = request.user.profile
    
    # âœ… Check if doctor has access to this patient
    if user_profile.has_role('doctor'):
        doctor = user_profile.doctor
        if doctor:
            # Check if this patient is assigned to this doctor
            has_access = Appointment.objects.filter(
                patient=patient,
                doctor=doctor
            ).exists()
            
            if not has_access:
                messages.error(request, 'âŒ You do not have access to this patient.')
                return redirect('patients:list')
        else:
            messages.error(request, 'âŒ No doctor profile found.')
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

    dental_chart_records = DentalChart.objects.filter(patient=patient).order_by('-updated_at')

    contact_access_approved = False
    pending_contact_request = None
    if is_doctor(request.user):
        contact_access_approved = PatientContactAccessRequest.objects.filter(patient=patient, requester=request.user, status='approved').exists()
        pending_contact_request = PatientContactAccessRequest.objects.filter(patient=patient, requester=request.user, status='pending').order_by('-requested_at').first()
        show_contact = contact_access_approved or user_profile.has_role('admin')
    else:
        show_contact = user_profile.has_permission('patients.contacts.view') or user_profile.has_role('admin')
    
    # Calculate total amount
    total_amount = invoices.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    # âœ… Get portal PIN if exists
    try:
        portal_access = patient.portal_access
        portal_pin = None
    except PatientPortalAccess.DoesNotExist:
        portal_pin = None
    
    # âœ… Get new patient PIN from session (if just created)
    new_patient_pin = request.session.pop('new_patient_pin', None)
    new_patient_id = request.session.pop('new_patient_id', None)
    

    context = {
        'patient': patient,
        'appointments': appointments,
        'treatments': treatments,
        'invoices': invoices,
        'total_amount': total_amount,
        'dental_chart_records': dental_chart_records,
        'dental_chart_count': dental_chart_records.count(),
        'is_doctor': user_profile.has_role('doctor'),
        'can_edit_patient': user_profile.has_permission('patients.edit'),
        'can_invoice_patient': user_profile.has_permission('billing.view'),
        'portal_pin': portal_pin,  # âœ… Pass portal PIN
        'new_patient_pin': new_patient_pin,  # âœ… Pass new patient PIN
        'new_patient_id': new_patient_id,  # âœ… Pass new patient ID
        'show_contact': show_contact,
        'pending_contact_request': pending_contact_request,
        'contact_access_approved': contact_access_approved,
        'can_request_contact': user_profile.has_permission('patients.contacts.request') and is_doctor(request.user),
    }
    return render(request, 'patients/detail.html', context)


# ====================
# PATIENT EDIT
# ====================

@login_required
def patient_edit(request, pk):
    """Edit patient information - Doctors are NOT allowed"""
    user_profile = request.user.profile
    
    # âœ… PREVENT doctors from editing patients
    if user_profile.has_role('doctor'):
        messages.error(request, 'âŒ Doctors are not allowed to edit patients.')
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
    
    # âœ… PREVENT doctors from deleting patients
    if user_profile.has_role('doctor'):
        messages.error(request, 'âŒ Doctors are not allowed to delete patients.')
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
def patient_status(request, pk):
    """Activate or deactivate a patient - Admin only."""
    patient = get_object_or_404(Patient, pk=pk)

    if not request.user.profile.has_permission('patients.status'):
        messages.error(request, 'âŒ Access denied. Only administrators can change patient status.')
        return redirect('patients:detail', pk=pk)

    if request.method == 'POST':
        patient.is_active = not patient.is_active
        patient.save(update_fields=['is_active'])
        status = 'activated' if patient.is_active else 'deactivated'
        messages.success(request, f'Patient {patient.full_name} has been {status} successfully.')

    return redirect('patients:detail', pk=pk)


@login_required
def patient_add_image(request, pk):
    """Add dental images - Doctors can add images to their patients"""
    patient = get_object_or_404(Patient, pk=pk)
    user_profile = request.user.profile
    
    # âœ… Check if doctor has access to this patient
    if user_profile.has_role('doctor'):
        doctor = user_profile.doctor
        if doctor:
            has_access = Appointment.objects.filter(
                patient=patient,
                doctor=doctor
            ).exists()
            if not has_access:
                messages.error(request, 'âŒ You do not have access to this patient.')
                return redirect('patients:list')
        else:
            messages.error(request, 'âŒ No doctor profile found.')
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
    # âœ… Only admin and receptionist can generate PINs
    if not request.user.profile.has_any_role(['admin', 'receptionist']):
        messages.error(request, 'âŒ Access denied. Only admin or receptionist can generate portal PINs.')
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
        messages.success(request, f'âœ… Portal PIN updated for {patient.full_name}. New PIN: {portal_pin}')
    else:
        messages.success(request, f'âœ… Portal access created for {patient.full_name}. PIN: {portal_pin}')
    
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
        
        # âœ… If doctor, only show assigned patients
        if user_profile.has_role('doctor'):
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
            latest_invoice = Invoice.objects.filter(
                patient=patient
            ).order_by('-issue_date', '-id').first()
            total_balance = latest_invoice.balance_due if latest_invoice else 0
            
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
            
            # âœ… Get portal PIN
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
                'portal_pin': portal_pin,  # âœ… Include portal PIN
            })
        
        return JsonResponse({'results': results})
        
    except Exception as e:
        print(f"Search API Error: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'results': [], 'error': str(e)}, status=500)



def get_tooth_name(tooth_number):
    """Get the clinical name of a permanent tooth using Universal Numbering."""

    tooth_names = {
        1: 'Right Maxillary 3rd Molar',
        2: 'Right Maxillary 2nd Molar',
        3: 'Right Maxillary 1st Molar',
        4: 'Right Maxillary 2nd Premolar',
        5: 'Right Maxillary 1st Premolar',
        6: 'Right Maxillary Canine',
        7: 'Right Maxillary Lateral Incisor',
        8: 'Right Maxillary Central Incisor',

        9: 'Left Maxillary Central Incisor',
        10: 'Left Maxillary Lateral Incisor',
        11: 'Left Maxillary Canine',
        12: 'Left Maxillary 1st Premolar',
        13: 'Left Maxillary 2nd Premolar',
        14: 'Left Maxillary 1st Molar',
        15: 'Left Maxillary 2nd Molar',
        16: 'Left Maxillary 3rd Molar',

        17: 'Left Mandibular 3rd Molar',
        18: 'Left Mandibular 2nd Molar',
        19: 'Left Mandibular 1st Molar',
        20: 'Left Mandibular 2nd Premolar',
        21: 'Left Mandibular 1st Premolar',
        22: 'Left Mandibular Canine',
        23: 'Left Mandibular Lateral Incisor',
        24: 'Left Mandibular Central Incisor',

        25: 'Right Mandibular Central Incisor',
        26: 'Right Mandibular Lateral Incisor',
        27: 'Right Mandibular Canine',
        28: 'Right Mandibular 1st Premolar',
        29: 'Right Mandibular 2nd Premolar',
        30: 'Right Mandibular 1st Molar',
        31: 'Right Mandibular 2nd Molar',
        32: 'Right Mandibular 3rd Molar',
    }

    return tooth_names.get(
        tooth_number,
        f'Tooth #{tooth_number}'
    )


@login_required
def dental_chart(request, pk):
    """View and edit a patient's 32-tooth odontogram."""
    from appointments.models import DentalChart

    patient = get_object_or_404(Patient, pk=pk)
    user_profile = request.user.profile

    # Doctors may only access their assigned patients.
    # Admins have full access.
    if user_profile.has_role('doctor'):
        doctor = user_profile.doctor
        if not doctor or not Appointment.objects.filter(
            patient=patient,
            doctor=doctor
        ).exists():
            messages.error(
                request,
                '❌ You do not have access to this patient.'
            )
            return redirect('patients:list')

    # Only doctors and admins can edit dental-chart records.
    can_edit = user_profile.has_permission('dental.edit')

    if request.method == 'POST':
        if not can_edit:
            messages.error(
                request,
                '❌ Only doctors and administrators can update dental charts.'
            )
            return redirect(
                'patients:dental_chart',
                pk=patient.pk
            )

        try:
            tooth_number = int(
                request.POST.get('tooth_number', '0')
            )
            condition = request.POST.get(
                'condition',
                ''
            ).strip()
            surface = request.POST.get(
                'surface',
                ''
            ).strip() or None
            notes = request.POST.get(
                'notes',
                ''
            ).strip()

            if tooth_number < 1 or tooth_number > 32 or not condition:
                messages.error(
                    request,
                    'Tooth number and condition are required.'
                )
                return redirect(
                    'patients:dental_chart',
                    pk=patient.pk
                )

            record, created = DentalChart.objects.update_or_create(
                patient=patient,
                tooth_number=tooth_number,
                defaults={
                    'tooth_name': get_tooth_name(tooth_number),
                    'condition': condition,
                    'surface': surface,
                    'notes': notes,
                    'created_by': request.user,
                }
            )

            action = 'recorded' if created else 'updated'

            messages.success(
                request,
                f'✅ Tooth #{tooth_number} {action} as '
                f'{record.get_condition_display()}.'
            )

            return redirect(
                'patients:dental_chart',
                pk=patient.pk
            )

        except (ValueError, TypeError):
            messages.error(
                request,
                '❌ Invalid tooth number.'
            )

        except Exception as e:
            messages.error(
                request,
                f'❌ Error updating dental chart: {str(e)}'
            )

    # Existing dental-chart records
    chart_records = (
        DentalChart.objects
        .filter(patient=patient)
        .select_related('created_by')
    )

    tooth_map = {
        record.tooth_number: record
        for record in chart_records
    }

    # Universal numbering arranged by quadrant.
    quadrant_numbers = [
        (
            'Upper Right',
            'Maxilla',
            list(range(8, 0, -1))
        ),
        (
            'Upper Left',
            'Maxilla',
            list(range(9, 17))
        ),
        (
            'Lower Left',
            'Mandible',
            list(range(17, 25))
        ),
        (
            'Lower Right',
            'Mandible',
            list(range(32, 24, -1))
        ),
    ]

    # Build the quadrant data used by the template.
    quadrants = []

    for qname, arch, numbers in quadrant_numbers:
        quadrants.append({
            'name': qname,
            'arch': arch,
            'teeth': [
                tooth_map.get(num) or num
                for num in numbers
            ],
        })

    # Build complete 32-tooth data.
    tooth_data = []

    for num in range(1, 33):
        record = tooth_map.get(num)

        tooth_data.append({
            'number': num,
            'has_record': bool(record),
            'condition_display': (
                record.get_condition_display()
                if record else None
            ),
            'condition': (
                record.condition
                if record else ''
            ),
            'surface': (
                record.surface
                if record else ''
            ),
            'notes': (
                record.notes
                if record else ''
            ),
            'tooth_name': (
                record.tooth_name
                if record
                else get_tooth_name(num)
            ),
            'updated_at': (
                record.updated_at
                if record
                else None
            ),
        })

    context = {
        'patient': patient,
        'tooth_data': tooth_data,
        'tooth_map': tooth_map,
        'quadrants': quadrants,
        'is_doctor': user_profile.has_role('doctor'),
        'can_edit_patient': user_profile.has_permission('patients.edit'),
        'can_invoice_patient': user_profile.has_permission('billing.view'),
        'can_edit': can_edit,
        'recorded_count': len(chart_records),
        'remaining_count': 32 - len(chart_records),
        'condition_choices': DentalChart.TOOTH_CONDITION_CHOICES,
        'surface_choices': DentalChart.SURFACE_CHOICES,
    }

    return render(
        request,
        'patients/dental_chart.html',
        context
    )