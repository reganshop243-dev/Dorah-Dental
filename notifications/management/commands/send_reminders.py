from django.core.management.base import BaseCommand
from notifications.services import send_appointment_reminders


class Command(BaseCommand):
    help = 'Send appointment reminders to patients'

    def handle(self, *args, **options):
        self.stdout.write('Sending appointment reminders...')
        send_appointment_reminders()
        self.stdout.write(self.style.SUCCESS('Reminders sent successfully!'))