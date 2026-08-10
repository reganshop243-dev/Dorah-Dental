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


# ====================
# PATIENT LIST
# ====================

@login_required
def patient_list(request):
    """Display all active patients with balances"""
    patients = Patient.objects.filter(is_active=True).order_by('-registered_at')
    
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
    }
    return render(request, 'patients/list.html', context)


# ====================
# PATIENT ADD
# ====================

@login_required
def patient_add(request):
    """Add a new patient with dental images and support for age input"""
    if request.method == 'POST':
        try:
            # Personal Information
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            date_of_birth = request.POST.get('date_of_birth')
            age_years = request.POST.get('age_years', '')
            gender = request.POST.get('gender')
            
            # Contact Information
            phone = request.POST.get('phone', '').strip()
            email = request.POST.get('email', '').strip()
            address = request.POST.get('address', '').strip()
            
            # Emergency Contact / Next of Kin
            next_of_kin = request.POST.get('next_of_kin', '').strip()
            next_of_kin_contact = request.POST.get('next_of_kin_contact', '').strip()
            
            # Medical History
            under_physician = request.POST.get('under_physician', '')
            physician_details = request.POST.get('physician_details', '').strip()
            allergies = request.POST.get('allergies', '').strip()
            current_medications = request.POST.get('current_medications', '').strip()
            
            # Dental History
            dental_discomfort = request.POST.get('dental_discomfort', '')
            discomfort_details = request.POST.get('discomfort_details', '').strip()
            previous_surgery = request.POST.get('previous_surgery', '')
            surgery_details = request.POST.get('surgery_details', '').strip()
            reason_for_visit = request.POST.get('reason_for_visit', '').strip()
            last_dental_visit = request.POST.get('last_dental_visit', '')
            
            # Backdated registration date
            registered_at = request.POST.get('registered_at', '')
            
            # Validate required fields
            if not first_name:
                messages.error(request, 'First name is required')
                return render(request, 'patients/add.html')
            
            if not last_name:
                messages.error(request, 'Last name is required')
                return render(request, 'patients/add.html')
            
            if not gender:
                messages.error(request, 'Gender is required')
                return render(request, 'patients/add.html')
            
            if not phone:
                messages.error(request, 'Phone number is required')
                return render(request, 'patients/add.html')
            
            if not reason_for_visit:
                messages.error(request, 'Reason for visit is required')
                return render(request, 'patients/add.html')
            
            # Validate date of birth OR age
            if not date_of_birth and not age_years:
                messages.error(request, 'Either Date of Birth or Age in Years is required')
                return render(request, 'patients/add.html')
            
            # Convert age to years if provided
            if age_years:
                try:
                    age_years = int(age_years)
                    if age_years < 0 or age_years > 150:
                        messages.error(request, 'Please enter a valid age between 0 and 150')
                        return render(request, 'patients/add.html')
                except ValueError:
                    messages.error(request, 'Please enter a valid number for age')
                    return render(request, 'patients/add.html')
            else:
                age_years = None
            
            # Create patient
            patient = Patient.objects.create(
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth or None,
                age_years=age_years,
                gender=gender,
                phone=phone,
                email=email or None,
                address=address or None,
                next_of_kin=next_of_kin or None,
                next_of_kin_contact=next_of_kin_contact or None,
                under_physician=under_physician or None,
                physician_details=physician_details or None,
                allergies=allergies or '',
                current_medications=current_medications or None,
                reason_for_visit=reason_for_visit or None,
                dental_discomfort=dental_discomfort or None,
                discomfort_details=discomfort_details or None,
                last_dental_visit=last_dental_visit or None,
                is_active=True
            )
            
            # Handle backdated registration date
            if registered_at:
                try:
                    registered_datetime = datetime.strptime(registered_at, '%Y-%m-%d')
                    patient.registered_at = registered_datetime
                    patient.save()
                except ValueError:
                    pass  # If invalid format, keep the default (now)
            
            # Handle dental images
            image_files = request.FILES.getlist('dental_images')
            if image_files:
                image_type = request.POST.get('image_type', 'clinical')
                image_description = request.POST.get('image_description', '')
                
                for image_file in image_files:
                    DentalImage.objects.create(
                        patient=patient,
                        image=image_file,
                        image_type=image_type,
                        description=image_description or f"Uploaded on {timezone.now().strftime('%Y-%m-%d')}",
                        uploaded_by=request.user
                    )
            
            messages.success(request, f'Patient {patient.full_name} registered successfully!')
            return redirect('patients:detail', pk=patient.pk)
            
        except Exception as e:
            messages.error(request, f'Error adding patient: {str(e)}')
            import traceback
            traceback.print_exc()
            return render(request, 'patients/add.html')
    
    return render(request, 'patients/add.html')


# ====================
# PATIENT DETAIL
# ====================

@login_required
def patient_detail(request, pk):
    """View patient details with appointment and treatment history"""
    patient = get_object_or_404(Patient, pk=pk)
    
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
    
    context = {
        'patient': patient,
        'appointments': appointments,
        'treatments': treatments,
        'invoices': invoices,
        'total_amount': total_amount,
    }
    return render(request, 'patients/detail.html', context)


# ====================
# PATIENT EDIT
# ====================

@login_required
def patient_edit(request, pk):
    """Edit patient information with profile picture"""
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
    """Archive/delete patient (soft delete)"""
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
    """Add dental images to an existing patient"""
    patient = get_object_or_404(Patient, pk=pk)
    
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
# PATIENT SEARCH (API)
# ====================

@login_required
def patient_search_api(request):
    """API endpoint for searching patients (for AJAX)"""
    try:
        query = request.GET.get('q', '').strip()
        balance_filter = request.GET.get('balance', '')
        sort = request.GET.get('sort', '-registered_at')
        
        # Base queryset - only active patients
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
            })
        
        return JsonResponse({'results': results})
        
    except Exception as e:
        print(f"Search API Error: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'results': [], 'error': str(e)}, status=500)