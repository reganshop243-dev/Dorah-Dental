from django.core.management.base import BaseCommand
from django.contrib import messages
from patients.models import Patient
from patient_portal.models import PatientPortalAccess
import random

class Command(BaseCommand):
    help = 'Generate portal PINs for all patients or specific patients'

    def add_arguments(self, parser):
        parser.add_argument('--patient_id', type=int, help='Specific patient ID')
        parser.add_argument('--all', action='store_true', help='Generate for all patients')

    def handle(self, *args, **options):
        if options['patient_id']:
            patients = Patient.objects.filter(pk=options['patient_id'], is_active=True)
        elif options['all']:
            patients = Patient.objects.filter(is_active=True)
        else:
            self.stdout.write(self.style.ERROR('Please specify --patient_id or --all'))
            return
        
        created_count = 0
        for patient in patients:
            portal_access, created = PatientPortalAccess.objects.get_or_create(
                patient=patient,
                defaults={
                    'portal_pin': f"{random.randint(100000, 999999)}",
                    'is_active': True
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created PIN for {patient.full_name}: {portal_access.portal_pin}'))
            else:
                self.stdout.write(f'Skipped {patient.full_name} - already has portal access')
        
        self.stdout.write(self.style.SUCCESS(f'Done! Created {created_count} portal accesses.'))