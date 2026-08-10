from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from appointments.models import Appointment
from notifications.services import NotificationService
from django.contrib import messages


class Command(BaseCommand):
    help = 'Send reminders for upcoming appointments (1-2 days from now)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=2,
            help='Number of days to look ahead (default: 2)'
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Test mode - do not send actual messages'
        )

    def handle(self, *args, **options):
        days = options.get('days', 2)
        test_mode = options.get('test', False)
        
        self.stdout.write('=' * 60)
        self.stdout.write('📱 Sending Upcoming Appointment Reminders')
        self.stdout.write('=' * 60)
        
        today = timezone.now().date()
        target_date = today + timedelta(days=days)
        
        self.stdout.write(f'📅 Today: {today}')
        self.stdout.write(f'📅 Sending reminders for: {target_date}')
        
        # Get appointments for the target date
        appointments = Appointment.objects.filter(
            appointment_date=target_date,
            status__in=['scheduled', 'checked_in'],
            send_reminder=True,
            reminder_sent=False
        )
        
        count = appointments.count()
        self.stdout.write(f'📊 Found {count} appointments')
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('✅ No reminders to send'))
            return
        
        sent_count = 0
        error_count = 0
        
        for appointment in appointments:
            self.stdout.write(f'\n📨 Processing: {appointment.patient.full_name} - {appointment.appointment_date}')
            
            if test_mode:
                self.stdout.write(f'   🔍 TEST MODE - Would send to: {appointment.patient.phone}')
                sent_count += 1
                continue
            
            try:
                service = NotificationService()
                service.send_appointment_reminder(appointment)
                
                # Mark as sent
                appointment.reminder_sent = True
                appointment.save()
                
                sent_count += 1
                self.stdout.write(self.style.SUCCESS(f'   ✅ Reminder sent to {appointment.patient.full_name}'))
                
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'   ❌ Failed: {str(e)}'))
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(f'📊 Summary:')
        self.stdout.write(f'   ✅ Sent: {sent_count}')
        self.stdout.write(f'   ❌ Failed: {error_count}')
        self.stdout.write('=' * 60)