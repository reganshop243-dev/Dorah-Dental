import logging
from django.http import JsonResponse
from django.db.models import Sum
from datetime import date

logger = logging.getLogger(__name__)

def simple_stats(request):
    logger.info("=" * 60)
    logger.info("🔵 SIMPLE STATS CALLED")
    logger.info(f"   Method: {request.method}")
    logger.info(f"   Path: {request.path}")
    logger.info(f"   User: {request.user}")
    logger.info(f"   Authenticated: {request.user.is_authenticated}")
    logger.info("=" * 60)
    
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
            'message': 'Debug stats - working!'
        }
        logger.info(f"✅ Data: {data}")
        return JsonResponse(data)
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)
