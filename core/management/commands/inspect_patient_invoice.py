"""
Diagnostic command: inspect how Patient <-> Invoice are linked
and whether the patient name is cached/denormalized on Invoice.

Run:
    python manage.py inspect_patient_invoice
    python manage.py inspect_patient_invoice --sample-invoice 12
"""

from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import models


class Command(BaseCommand):
    help = "Inspect Patient / Invoice models and detect stale patient names on invoices."

    def add_arguments(self, parser):
        parser.add_argument(
            '--sample-invoice',
            type=int,
            default=None,
            help='Show details for a single Invoice by ID.',
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def hr(self, title=''):
        line = '=' * 78
        self.stdout.write(self.style.MIGRATE_HEADING(line))
        if title:
            self.stdout.write(self.style.MIGRATE_HEADING(f'  {title}'))
            self.stdout.write(self.style.MIGRATE_HEADING(line))

    def ok(self, msg):
        self.stdout.write(self.style.SUCCESS(f'  [OK]   {msg}'))

    def warn(self, msg):
        self.stdout.write(self.style.WARNING(f'  [WARN] {msg}'))

    def err(self, msg):
        self.stdout.write(self.style.ERROR(f'  [ERR]  {msg}'))

    def info(self, msg):
        self.stdout.write(f'         {msg}')

    def describe_fields(self, model):
        """Print every field of a model with its type and useful flags."""
        self.stdout.write(f'  Model: {model._meta.label}')
        self.stdout.write(f'  DB table: {model._meta.db_table}')
        for f in model._meta.get_fields():
            if not hasattr(f, 'get_internal_type'):
                # reverse relations / m2m don't have this
                kind = type(f).__name__
                self.info(f'- {f.name:<28} {kind}')
                continue
            flags = []
            if getattr(f, 'primary_key', False):
                flags.append('pk')
            if getattr(f, 'unique', False):
                flags.append('unique')
            if getattr(f, 'null', False):
                flags.append('null')
            if getattr(f, 'blank', False):
                flags.append('blank')
            if getattr(f, 'is_relation', False):
                flags.append(f'-> {getattr(f.remote_field.model, "__name__", "?")}')
            flag_str = f'  [{", ".join(flags)}]' if flags else ''
            self.info(
                f'- {f.name:<28} {f.get_internal_type():<18}'
                f'{flag_str}'
            )
        self.stdout.write('')

    # ------------------------------------------------------------------ #
    # Main
    # ------------------------------------------------------------------ #
    def handle(self, *args, **options):
        # ---- Resolve the models ------------------------------------- #
        try:
            Patient = apps.get_model('patients', 'Patient')
        except LookupError:
            self.err("Could not find model 'patients.Patient'.")
            return

        try:
            Invoice = apps.get_model('billing', 'Invoice')
        except LookupError:
            self.err("Could not find model 'billing.Invoice'.")
            return

        # ================================================================ #
        self.hr('1. PATIENT MODEL')
        self.describe_fields(Patient)

        # ================================================================ #
        self.hr('2. INVOICE MODEL')
        self.describe_fields(Invoice)

        # ================================================================ #
        self.hr('3. LINK BETWEEN INVOICE AND PATIENT')

        invoice_field_names = {f.name for f in Invoice._meta.get_fields()}
        patient_field_names = {f.name for f in Patient._meta.get_fields()}

        # ForeignKey to Patient?
        fk_to_patient = None
        for f in Invoice._meta.get_fields():
            if isinstance(f, models.ForeignKey):
                if f.remote_field.model._meta.label == Patient._meta.label:
                    fk_to_patient = f
                    break

        if fk_to_patient:
            self.ok(
                f"Invoice has ForeignKey '{fk_to_patient.name}' -> "
                f"{Patient._meta.label} "
                f"(on_delete={fk_to_patient.remote_field.on_delete.__name__}, "
                f"null={fk_to_patient.null})"
            )
        else:
            self.err(
                "Invoice has NO ForeignKey to Patient. "
                "The link must be made by name/MRN string — fragile."
            )

        # Denormalized name fields on Invoice?
        name_like = [
            f for f in Invoice._meta.get_fields()
            if hasattr(f, 'get_internal_type')
            and f.get_internal_type() in ('CharField', 'TextField')
            and any(k in f.name.lower() for k in ('name', 'patient'))
            and not f.is_relation
        ]

        if name_like:
            self.warn(
                f"Invoice has {len(name_like)} cached name-like field(s): "
                + ", ".join(f.name for f in name_like)
            )
            self.info(
                "These are probably denormalized copies of the patient name "
                "that will go stale when the Patient is edited."
            )
        else:
            self.ok("Invoice has no cached name fields.")

        # ================================================================ #
        self.hr('4. LIVE DATA CHECK')

        total_patients = Patient.objects.count()
        total_invoices = Invoice.objects.count()
        self.info(f'Patients: {total_patients}')
        self.info(f'Invoices: {total_invoices}')
        self.stdout.write('')

        if not fk_to_patient:
            self.warn("No FK to Patient — cannot auto-check for stale names.")
            return

        fk_name = fk_to_patient.name
        # Field names we'll try to compare
        candidate_fields = [f.name for f in name_like]

        if not candidate_fields:
            self.ok(
                "No cached name fields to check. "
                "Templates should use invoice.patient.first_name / last_name."
            )
            # Still sample a couple of invoices for confirmation
            for inv in Invoice.objects.select_related(fk_name)[:3]:
                p = getattr(inv, fk_name, None)
                if p:
                    live = f'{p.first_name} {p.last_name}'.strip()
                    self.info(f'Invoice #{inv.pk}: live name = {live!r}')
            return

        # We have both a FK and cached fields -> compare them.
        mismatches = []
        checked = 0
        for inv in Invoice.objects.select_related(fk_name).iterator():
            p = getattr(inv, fk_name, None)
            if not p:
                continue
            live = f'{p.first_name} {p.last_name}'.strip()
            for field_name in candidate_fields:
                cached = getattr(inv, field_name, None)
                if cached is None:
                    continue
                if str(cached).strip() != live:
                    mismatches.append((inv.pk, field_name, cached, live))
            checked += 1

        self.info(f'Invoices checked: {checked}')

        if not mismatches:
            self.ok('No stale names found — cached fields match the live patient.')
            return

        self.err(f'Found {len(mismatches)} stale invoice name(s):')
        for inv_id, field_name, cached, live in mismatches[:20]:
            self.info(
                f'Invoice #{inv_id}  {field_name} = {cached!r}  '
                f'!= live {live!r}'
            )
        if len(mismatches) > 20:
            self.info(f'... and {len(mismatches) - 20} more.')

        # ================================================================ #
        self.hr('5. SUGGESTED FIX')
        self.info('Add a post_save signal on Patient that updates Invoice:')
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO(
            "  # patients/signals.py\n"
            "  from django.db.models.signals import post_save\n"
            "  from django.dispatch import receiver\n"
            "  from .models import Patient\n"
            "\n"
            "  @receiver(post_save, sender=Patient)\n"
            "  def sync_patient_name_to_invoices(sender, instance, **kwargs):\n"
            "      from billing.models import Invoice\n"
            f"      full_name = f'{{instance.first_name}} {{instance.last_name}}'.strip()\n"
            f"      Invoice.objects.filter({fk_name}=instance).update(\n"
            + ''.join(
                f"          {f} = full_name,\n" for f in candidate_fields
            )
            + "      )\n"
        ))
        self.stdout.write('')
        self.info('Then wire it up in patients/apps.py:')
        self.stdout.write(self.style.HTTP_INFO(
            "  class PatientsConfig(AppConfig):\n"
            "      def ready(self):\n"
            "          import patients.signals  # noqa\n"
        ))
        self.info("And set INSTALLED_APPS to 'patients.apps.PatientsConfig'.")

        # ================================================================ #
        if options.get('sample_invoice'):
            self.hr(f'6. SAMPLE INVOICE #{options["sample_invoice"]}')
            try:
                inv = Invoice.objects.select_related(fk_name).get(
                    pk=options['sample_invoice']
                )
            except Invoice.DoesNotExist:
                self.err(f'Invoice #{options["sample_invoice"]} does not exist.')
                return

            p = getattr(inv, fk_name, None)
            live = f'{p.first_name} {p.last_name}'.strip() if p else 'n/a'
            self.info(f'Invoice PK: {inv.pk}')
            self.info(f'Patient FK ({fk_name}): {getattr(inv, fk_name + "_id", "n/a")}')
            self.info(f'Live patient name: {live!r}')
            for field_name in candidate_fields:
                self.info(f'{field_name} (cached): {getattr(inv, field_name, None)!r}')
            self.info('Other invoice fields:')
            for f in Invoice._meta.get_fields():
                if not hasattr(f, 'get_internal_type'):
                    continue
                if f.name in candidate_fields or f.name == fk_name:
                    continue
                try:
                    self.info(f'  {f.name} = {getattr(inv, f.name)!r}')
                except Exception as e:
                    self.info(f'  {f.name} = <error: {e}>')