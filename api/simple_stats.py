from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from datetime import date
from django.db.models import Sum

@api_view(['GET'])
@permission_classes([AllowAny])
def stats(request):
    from patients.models import Patient
    from appointments.models import Appointment, Service, Doctor
    from billing.models import Invoice
    
    today = date.today()
    
    return Response({
        'total_patients': Patient.objects.filter(is_active=True).count(),
        'total_appointments_today': Appointment.objects.filter(appointment_date=today).count(),
        'total_services': Service.objects.filter(is_active=True).count(),
        'total_doctors': Doctor.objects.filter(is_active=True).count(),
        'revenue_today': Invoice.objects.filter(
            status='paid',
            payment_date=today
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'message': 'Stats endpoint - working!'
    })
