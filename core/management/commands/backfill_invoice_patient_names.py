"""
One-off backfill: sync Invoice.patient_name / patient_phone
to match the current Patient record.

Run (dry run first):
    python manage.py backfill_invoice_patient_names --dry-run

Then for real:
    python manage.py backfill_invoice_patient_names
"""

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Backfill Invoice.patient_name and patient_phone from the linked Patient."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would change without writing to the database.',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='How many invoices to process per DB round trip (default: 500).',
        )

    def handle(self, *args, **options):
        from billing.models import Invoice

        dry_run = options['dry_run']
        batch_size = options['batch_size']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be saved.\n'))

        qs = Invoice.objects.select_related('patient').only(
            'id', 'patient_name', 'patient_phone',
            'patient__id', 'patient__first_name', 'patient__last_name', 'patient__phone',
        )

        total = qs.count()
        self.stdout.write(f'Invoices to process: {total}')

        to_update = []
        changed = 0

        for inv in qs.iterator(chunk_size=batch_size):
            p = inv.patient
            if p is None:
                continue
            new_name = f"{p.first_name or ''} {p.last_name or ''}".strip()
            new_phone = p.phone or ''

            if (inv.patient_name or '') == new_name and (inv.patient_phone or '') == new_phone:
                continue

            inv.patient_name = new_name
            inv.patient_phone = new_phone
            to_update.append(inv)
            changed += 1

            if len(to_update) >= batch_size and not dry_run:
                with transaction.atomic():
                    Invoice.objects.bulk_update(
                        to_update, ['patient_name', 'patient_phone'], batch_size=batch_size
                    )
                self.stdout.write(f'  ... updated {changed} so far')
                to_update.clear()

        if not dry_run and to_update:
            with transaction.atomic():
                Invoice.objects.bulk_update(
                    to_update, ['patient_name', 'patient_phone'], batch_size=batch_size
                )

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'\nDry run finished. Would update {changed} invoice(s).'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\nDone. Updated {changed} invoice(s).'
            ))