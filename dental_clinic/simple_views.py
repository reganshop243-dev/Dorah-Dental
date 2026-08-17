from django.http import JsonResponse
from django.db.models import Sum
from datetime import date

def stats_view(request):
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
