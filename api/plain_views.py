from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
import json
from datetime import date
from django.db.models import Sum

# ==================== HELPER FUNCTIONS ====================

def get_patient_data():
    from patients.models import Patient
    patients = Patient.objects.filter(is_active=True)
    return [{
        'id': p.id,
        'first_name': p.first_name,
        'last_name': p.last_name,
        'phone': p.phone,
        'email': p.email,
        'gender': p.gender,
        'registered_at': p.registered_at.strftime('%Y-%m-%d') if p.registered_at else None,
    } for p in patients]

def get_appointment_data():
    from appointments.models import Appointment
    appointments = Appointment.objects.all().order_by('-appointment_date')
    return [{
        'id': a.id,
        'patient_name': f"{a.patient.first_name} {a.patient.last_name}",
        'doctor_name': a.doctor.name if a.doctor else None,
        'service_name': a.service.name if a.service else None,
        'appointment_date': a.appointment_date.strftime('%Y-%m-%d') if a.appointment_date else None,
        'appointment_time': a.appointment_time.strftime('%H:%M') if a.appointment_time else None,
        'status': a.status,
    } for a in appointments]

def get_service_data():
    from appointments.models import Service
    services = Service.objects.filter(is_active=True)
    return [{
        'id': s.id,
        'name': s.name,
        'description': s.description,
        'price': float(s.price),
        'duration_minutes': s.duration_minutes,
    } for s in services]

def get_doctor_data():
    from appointments.models import Doctor
    doctors = Doctor.objects.filter(is_active=True)
    return [{
        'id': d.id,
        'name': d.name,
        'specialization': d.specialization,
        'phone': d.phone,
        'email': d.email,
    } for d in doctors]

def get_invoice_data():
    from billing.models import Invoice
    invoices = Invoice.objects.all().order_by('-issue_date')
    return [{
        'id': i.id,
        'invoice_number': i.invoice_number,
        'patient_name': i.patient_name,
        'total_amount': float(i.total_amount),
        'status': i.status,
        'issue_date': i.issue_date.strftime('%Y-%m-%d') if i.issue_date else None,
    } for i in invoices]

# ==================== PUBLIC ENDPOINTS ====================

@csrf_exempt
@require_http_methods(["GET"])
def public_patients(request):
    try:
        data = get_patient_data()
        return JsonResponse({'results': data, 'count': len(data)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def public_appointments(request):
    try:
        data = get_appointment_data()
        return JsonResponse({'results': data, 'count': len(data)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def public_services(request):
    try:
        data = get_service_data()
        return JsonResponse({'results': data, 'count': len(data)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def public_doctors(request):
    try:
        data = get_doctor_data()
        return JsonResponse({'results': data, 'count': len(data)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def public_invoices(request):
    try:
        data = get_invoice_data()
        return JsonResponse({'results': data, 'count': len(data)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def public_stats(request):
    try:
        from patients.models import Patient
        from appointments.models import Appointment, Service, Doctor
        from billing.models import Invoice
        
        today = date.today()
        
        data = {
            'total_patients': Patient.objects.filter(is_active=True).count(),
            'total_appointments_today': Appointment.objects.filter(appointment_date=today).count(),
            'total_services': Service.objects.filter(is_active=True).count(),
            'total_doctors': Doctor.objects.filter(is_active=True).count(),
            'revenue_today': Invoice.objects.filter(
                status='paid',
                payment_date=today
            ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
            'message': 'Stats working!'
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ==================== LOGIN ENDPOINT ====================

@csrf_exempt
@require_http_methods(["POST"])
def public_login(request):
    try:
        body = json.loads(request.body)
        username = body.get('username')
        password = body.get('password')
        
        if not username or not password:
            return JsonResponse({'error': 'Username and password required'}, status=400)
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            token, created = Token.objects.get_or_create(user=user)
            
            try:
                profile = user.profile
                role = profile.role if hasattr(profile, 'role') else 'user'
                phone = profile.phone if hasattr(profile, 'phone') else ''
            except:
                role = 'user'
                phone = ''
            
            return JsonResponse({
                'token': token.key,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': role,
                    'phone': phone,
                }
            })
        else:
            return JsonResponse({'error': 'Invalid credentials'}, status=401)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
