from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import NotificationSetting, NotificationLog
from .services import NotificationService
from appointments.models import Appointment

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def notification_settings(request):
    if request.method == 'GET':
        settings = NotificationSetting.objects.first()
        if not settings:
            settings = NotificationSetting.objects.create()
        return Response({
            'enable_reminders': settings.enable_reminders,
            'reminder_hours_before': settings.reminder_hours_before,
            'channel': settings.channel,
            'email_subject': settings.email_subject,
        })
    
    # POST - Update settings
    data = request.data
    settings = NotificationSetting.objects.first()
    if not settings:
        settings = NotificationSetting.objects.create()
    
    settings.enable_reminders = data.get('enable_reminders', settings.enable_reminders)
    settings.reminder_hours_before = data.get('reminder_hours_before', settings.reminder_hours_before)
    settings.channel = data.get('channel', settings.channel)
    settings.email_subject = data.get('email_subject', settings.email_subject)
    settings.save()
    
    return Response({'message': 'Settings updated successfully'})

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_reminder(request, pk):
    try:
        appointment = Appointment.objects.get(pk=pk)
        service = NotificationService()
        service.send_appointment_reminder(appointment)
        return Response({'message': 'Reminder sent successfully'})
    except Appointment.DoesNotExist:
        return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def upcoming_reminders(request):
    from django.utils import timezone
    from datetime import timedelta
    
    today = timezone.now().date()
    appointments = Appointment.objects.filter(
        appointment_date__gte=today,
        appointment_date__lte=today + timedelta(days=7),
        status__in=['scheduled', 'checked_in']
    ).values('id', 'patient__first_name', 'patient__last_name', 'appointment_date', 'appointment_time')
    
    return Response(list(appointments))
