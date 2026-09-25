from decimal import Decimal, InvalidOperation
from datetime import datetime, date, time, timedelta
from pathlib import Path
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, close_old_connections, connection
from django.db.utils import OperationalError, InterfaceError
from django.contrib.auth.models import User
from django.utils import timezone

from patients.models import Patient
from appointments.models import Appointment, Doctor, Service, Treatment
from billing.models import Invoice, InvoiceItem, Payment

try:
    import openpyxl
except ImportError:
    openpyxl = None

SERVICE_NAMES = [
    'BRACES', 'BRACES METALLIC', 'BRACES REVIEW', 'SCALING', 'POLISHING',
    'RCT', 'EXTRACTION', 'WHITENING', 'DENTAL CHECK UP', 'X RAY', 'KIT',
    'REVIEW', 'SP 10', 'SP 6', 'DENTURES',
]

SERVICE_MAP = [
    ('BRACES AND KIT', 'BRACES METALLIC'),
    ('BRACES METALLIC', 'BRACES METALLIC'),
    ('BRACES REVIEW', 'BRACES REVIEW'),
    ('BRACES', 'BRACES'),
    ('SCALING AND POLISHING', 'SCALING'),
    ('SCALING', 'SCALING'),
    ('POLISHING', 'POLISHING'),
    ('RCT', 'RCT'),
    ('EXTRACTION', 'EXTRACTION'),
    ('X RAY', 'X RAY'),
    ('FILLINGS', 'DENTAL CHECK UP'),
    ('FILLING', 'DENTAL CHECK UP'),
    ('CHECK UP', 'DENTAL CHECK UP'),
    ('DENTAL CHECK UP', 'DENTAL CHECK UP'),
    ('SP 10', 'WHITENING'),
    ('SP 6', 'SCALING'),
    ('DENTURES', 'DENTURES'),
    ('RETAINERS', 'BRACES REVIEW'),
    ('REVIEW', 'BRACES REVIEW'),
    ('CROWN', 'DENTAL CHECK UP'),
    ('BRIDGE', 'DENTAL CHECK UP'),
]

def clean_text(value):
    if value is None:
        return ''
    return re.sub(r'\s+', ' ', str(value)).strip()

def normalize_name(value):
    return clean_text(value).upper()

def normalize_gender(value):
    value = clean_text(value).lower()
    if value.startswith('m'):
        return 'M'
    if value.startswith('f'):
        return 'F'
    return 'O'

def clean_phone(value):
    if value is None:
        return ''
    raw = clean_text(value)
    if not raw:
        return ''
    parts = re.split(r'[/,;]|\s+and\s+', raw, flags=re.I)
    first = re.sub(r'\D', '', parts[0])
    if first.startswith('256'):
        return '+' + first
    if first.startswith('0') and len(first) >= 9:
        return '+256' + first[1:]
    if first.startswith('7') and len(first) >= 9:
        return '+256' + first
    return first

def split_name(full_name):
    parts = normalize_name(full_name).split()
    if not parts:
        return 'UNKNOWN', ''
    if len(parts) == 1:
        return parts[0], ''
    return parts[0], ' '.join(parts[1:])

def parse_money(value):
    if value is None:
        return Decimal('0')
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = clean_text(value).upper().replace(',', '').replace('UGX', '')
    if text in ('', 'NIL', 'NONE', '-', 'N/A'):
        return Decimal('0')
    try:
        return Decimal(text)
    except InvalidOperation:
        return Decimal('0')

def parse_corrected_date(value):
    """
    Read the DATE column from the corrected workbook.

    The corrected workbook already contains real Excel date values with
    the register interpreted as DAY/MONTH/YEAR. We do not reinterpret
    numeric Excel serials here.
    """
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = clean_text(value)
    if not text:
        return None
    for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y'):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None

def service_for(treatment):
    text = normalize_name(treatment)
    for key, target in SERVICE_MAP:
        if key in text:
            return target
    return 'DENTAL CHECK UP'

def doctor_name_for(raw):
    text = normalize_name(raw)
    if not text:
        return 'UNASSIGNED'
    if ' AND ' in text:
        text = text.split(' AND ', 1)[0].strip()
    return re.sub(r'^DR\.?\s+', '', text)

def tx_from_notes(notes):
    match = re.search(r'transaction_id=(TX-\d+)', notes or '')
    return match.group(1) if match else None

class Command(BaseCommand):
    help = "Import Dorah's Dental Gem historical register from the corrected D/M/Y workbook."

    def add_arguments(self, parser):
        parser.add_argument(
            'file',
            nargs='?',
            default='Dorah_Dental_Register_DMY_Corrected.xlsx',
        )
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete patients, visits, treatments, invoices, invoice items and payments. Users are preserved.',
        )
        parser.add_argument('--no-visits', action='store_true')
        parser.add_argument('--no-billing', action='store_true')
        parser.add_argument('--created-by', default='')
        parser.add_argument('--limit', type=int, default=0)
        parser.add_argument('--start', type=int, default=1)
        parser.add_argument('--batch-size', type=int, default=200)

    def handle(self, *args, **options):
        if openpyxl is None:
            raise CommandError(
                'openpyxl is required. Install it with: python -m pip install openpyxl'
            )

        source = Path(options['file']).expanduser()
        if not source.exists():
            raise CommandError(f'Excel file not found: {source}')

        self.stdout.write(self.style.NOTICE(
            f'Loading corrected register: {source}'
        ))

        wb = openpyxl.load_workbook(
            source, data_only=True, read_only=True
        )

        if 'TRANSACTIONS' not in wb.sheetnames:
            raise CommandError(
                "Corrected workbook must contain a 'TRANSACTIONS' sheet."
            )

        ws = wb['TRANSACTIONS']
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            raise CommandError('The TRANSACTIONS sheet is empty.')

        headers = [clean_text(x).upper() for x in rows[0]]
        required = [
            'TRANSACTION_ID', 'SOURCE_ROW', 'DATE', 'NAMES', 'GENDER',
            'TREATMENT', 'ADDRESS', 'OFFER', 'AMOUNT_PAID', 'BALANCE',
            'DOCTOR', 'CONTACT',
        ]
        missing = [x for x in required if x not in headers]
        if missing:
            raise CommandError(
                f"TRANSACTIONS is missing required columns: {', '.join(missing)}"
            )
        idx = {name: headers.index(name) for name in required}

        creator = None
        if options['created_by']:
            creator = User.objects.filter(
                username=options['created_by']
            ).first()
            if not creator:
                raise CommandError(
                    f"User '{options['created_by']}' does not exist."
                )

        stats = {
            'rows': 0,
            'patients_created': 0,
            'patients_reused': 0,
            'visits_created': 0,
            'treatments_created': 0,
            'invoices_created': 0,
            'payments_created': 0,
            'doctors_created': 0,
            'services_created': 0,
            'warnings': 0,
        }
        warnings = []
        parsed = []

        # Read the already-corrected transactions. No MM/DD conversion occurs.
        for excel_row, row in enumerate(rows[1:], start=2):
            values = list(row)
            values += [None] * max(0, len(required) - len(values))

            tx_id = clean_text(values[idx['TRANSACTION_ID']])
            name = clean_text(values[idx['NAMES']])
            visit_date = parse_corrected_date(values[idx['DATE']])

            if not tx_id or not name:
                continue

            if not re.fullmatch(r'TX-\d{6}', tx_id):
                warnings.append(
                    f'Row {excel_row}: invalid transaction ID {tx_id!r}.'
                )
                continue

            if visit_date is None:
                warnings.append(
                    f'Row {excel_row}: {tx_id} has no valid D/M/Y date.'
                )
                continue

            parsed.append({
                'tx_id': tx_id,
                'row': int(values[idx['SOURCE_ROW']]) if values[idx['SOURCE_ROW']] else excel_row,
                'date': visit_date,
                'name': name,
                'gender': normalize_gender(values[idx['GENDER']]),
                'treatment': clean_text(values[idx['TREATMENT']]),
                'address': clean_text(values[idx['ADDRESS']]),
                'offer': clean_text(values[idx['OFFER']]),
                'paid': parse_money(values[idx['AMOUNT_PAID']]),
                'balance': parse_money(values[idx['BALANCE']]),
                'doctor_raw': clean_text(values[idx['DOCTOR']]),
                'doctor': doctor_name_for(values[idx['DOCTOR']]),
                'phone': clean_phone(values[idx['CONTACT']]),
                'contact_raw': clean_text(values[idx['CONTACT']]),
            })

        tx_seen = set()
        for item in parsed:
            if item['tx_id'] in tx_seen:
                warnings.append(
                    f"Duplicate transaction ID in workbook: {item['tx_id']}"
                )
            tx_seen.add(item['tx_id'])

        if len(parsed) != 2286:
            warnings.append(
                f'Expected 2286 transaction rows; parsed {len(parsed)}.'
            )

        dates = sorted({x['date'] for x in parsed})
        december_rows = [x for x in parsed if x['date'].month == 12]
        future_rows = [x for x in parsed if x['date'].year > 2026]

        if december_rows:
            warnings.append(
                f'Unexpected December transactions found: {len(december_rows)}.'
            )
        if future_rows:
            warnings.append(
                f'Unexpected dates after 2026 found: {len(future_rows)}.'
            )

        start = max(1, int(options.get('start', 1)))
        if start > 1:
            parsed = parsed[start - 1:]
        if options['limit'] and options['limit'] > 0:
            parsed = parsed[:options['limit']]

        # ============================================================
        # PRE-FLIGHT: validate database string lengths BEFORE reset.
        # This prevents a long import from failing hours later.
        # ============================================================
        length_errors = []

        def check_model_length(model, field_name, value, label):
            if value in (None, ''):
                return
            try:
                max_length = model._meta.get_field(field_name).max_length
            except Exception:
                max_length = None
            if max_length and len(str(value)) > max_length:
                length_errors.append(
                    f"{label}: {len(str(value))} chars exceeds {max_length}"
                )

        for item in parsed:
            first, last = split_name(item['name'])
            phone = (item['phone'] or '')[:20]
            doctor_name = item['doctor']
            service_name = service_for(item['treatment'])
            total_amount = item['paid'] + item['balance']

            check_model_length(Patient, 'first_name', first, f"{item['tx_id']} Patient.first_name")
            check_model_length(Patient, 'last_name', last, f"{item['tx_id']} Patient.last_name")
            check_model_length(Patient, 'phone', phone, f"{item['tx_id']} Patient.phone")
            check_model_length(Doctor, 'name', doctor_name, f"{item['tx_id']} Doctor.name")
            check_model_length(Service, 'name', service_name, f"{item['tx_id']} Service.name")
            check_model_length(Appointment, 'notification_phone', phone, f"{item['tx_id']} Appointment.notification_phone")
            check_model_length(Invoice, 'invoice_number', f"REG-{item['tx_id']}", f"{item['tx_id']} Invoice.invoice_number")
            check_model_length(Invoice, 'patient_name', item['name'], f"{item['tx_id']} Invoice.patient_name")
            check_model_length(Invoice, 'patient_phone', phone, f"{item['tx_id']} Invoice.patient_phone")
            check_model_length(InvoiceItem, 'description', item['treatment'] or service_name, f"{item['tx_id']} InvoiceItem.description")

        if length_errors:
            preview = length_errors[:30]
            raise CommandError(
                "PRE-FLIGHT FAILED: values exceed database field lengths. "
                "NO DATABASE RESET WAS PERFORMED.\n" +
                "\n".join(f"  - {x}" for x in preview) +
                (f"\n  ... and {len(length_errors) - len(preview)} more." if len(length_errors) > len(preview) else "")
            )

        self.stdout.write(self.style.SUCCESS(
            f"PRE-FLIGHT OK: {len(parsed)} rows passed field-length validation."
        ))

        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(
                f'Validated {len(parsed)} corrected transaction rows.'
            ))
            self.stdout.write(f'Date groups: {len(dates)}')
            for d in dates:
                count = sum(1 for x in parsed if x['date'] == d)
                self.stdout.write(
                    f'  {d.strftime("%d/%m/%Y")}: {count} rows'
                )
            self.stdout.write(
                f'Rows with phone: {sum(bool(x["phone"]) for x in parsed)}'
            )
            self.stdout.write(
                f'Rows with balance: {sum(x["balance"] > 0 for x in parsed)}'
            )
            if warnings:
                self.stdout.write(
                    self.style.WARNING(f'Warnings: {len(warnings)}')
                )
                for warning in warnings[:30]:
                    self.stdout.write(f'  - {warning}')
            else:
                self.stdout.write(self.style.SUCCESS('No warnings.'))
            return

        # Database connectivity check BEFORE any reset.
        try:
            close_old_connections()
            connection.ensure_connection()
            self.stdout.write(self.style.SUCCESS(
                "PRE-FLIGHT OK: PostgreSQL connection is available."
            ))
        except (OperationalError, InterfaceError) as exc:
            raise CommandError(
                f"PRE-FLIGHT FAILED: PostgreSQL is not reachable. "
                f"NO DATABASE RESET WAS PERFORMED. {exc}"
            ) from exc

        if options['reset']:
            self.stdout.write(self.style.WARNING(
                'RESET: deleting patients, appointments, treatments, '
                'invoices, invoice items and payments. Users are preserved.'
            ))
            with transaction.atomic():
                Payment.objects.all().delete()
                InvoiceItem.objects.all().delete()
                Invoice.objects.all().delete()
                Treatment.objects.all().delete()
                Appointment.objects.all().delete()
                Patient.objects.all().delete()

        total = len(parsed)
        if total == 0:
            self.stdout.write(self.style.WARNING(
                'No transaction rows to import.'
            ))
            return

        batch_size = max(1, int(options['batch_size']))
        service_cache = {}
        doctor_cache = {}
        patient_by_phone = {}
        patient_by_name = {}
        imported_appointments = {}
        imported_invoices = {}
        appointment_slot_counts = {}

        # Live progress/ETA. This is terminal-only and does not change import data.
        import time as _time
        progress_started = _time.monotonic()
        progress_done = 0
        progress_every = 10

        close_old_connections()

        for service_name in SERVICE_NAMES:
            service = Service.objects.filter(name=service_name).first()
            if service is None:
                service = Service.objects.create(
                    name=service_name,
                    description=service_name,
                    price=Decimal('0'),
                    duration_minutes=30,
                    is_active=True,
                )
                stats['services_created'] += 1
            service_cache[service_name] = service

        for service in Service.objects.all():
            service_cache[service.name] = service

        for patient in Patient.objects.all().only(
            'id', 'first_name', 'last_name', 'phone', 'address',
            'gender', 'registered_at', 'reason_for_visit',
        ):
            name_key = normalize_name(
                f'{patient.first_name} {patient.last_name}'
            )
            patient_by_name.setdefault(name_key, patient.pk)
            if patient.phone:
                patient_by_phone.setdefault(patient.phone, patient.pk)
                if patient.phone.startswith('+256'):
                    patient_by_phone.setdefault(
                        '0' + patient.phone[4:], patient.pk
                    )

        for doctor in Doctor.objects.all():
            doctor_cache[doctor.name] = doctor.pk

        # Resume-safe: identify records using TX IDs, not old row markers.
        for appointment in Appointment.objects.filter(
            notes__contains='transaction_id=TX-'
        ).select_related('patient', 'doctor', 'service'):
            tx = tx_from_notes(appointment.notes)
            if tx:
                imported_appointments[tx] = appointment.pk

        for invoice in Invoice.objects.filter(
            notes__contains='transaction_id=TX-'
        ):
            tx = tx_from_notes(invoice.notes)
            if tx:
                imported_invoices[tx] = invoice.pk

        def import_batch(batch):
            """Bulk import one batch in a single transaction.

            All parent rows are created/resolved before dependent rows.  PostgreSQL
            returns primary keys from bulk_create, so appointments can safely feed
            treatments/invoices without the per-row transaction overhead.
            """
            nonlocal progress_done

            with transaction.atomic():
                # ------------------------------------------------------------
                # 1) Resolve/create services and doctors with minimal queries.
                # ------------------------------------------------------------
                needed_service_names = {service_for(x['treatment']) for x in batch}
                missing_services = [
                    name for name in needed_service_names
                    if name not in service_cache
                ]
                if missing_services:
                    Service.objects.bulk_create([
                        Service(
                            name=name, description=name, price=Decimal('0'),
                            duration_minutes=30, is_active=True,
                        ) for name in missing_services
                    ], ignore_conflicts=True)
                    stats['services_created'] += len(missing_services)
                    for service in Service.objects.filter(name__in=needed_service_names):
                        service_cache[service.name] = service

                needed_doctor_names = {x['doctor'] for x in batch}
                missing_doctors = [
                    name for name in needed_doctor_names
                    if name not in doctor_cache
                ]
                if missing_doctors:
                    Doctor.objects.bulk_create([
                        Doctor(name=name, is_active=True)
                        for name in missing_doctors
                    ], ignore_conflicts=True)
                    stats['doctors_created'] += len(missing_doctors)
                    for doctor in Doctor.objects.filter(name__in=needed_doctor_names):
                        doctor_cache[doctor.name] = doctor.pk

                # ------------------------------------------------------------
                # 2) Resolve existing patients from memory; bulk-create new ones.
                # ------------------------------------------------------------
                pending_patients = []
                pending_keys = set()
                row_patient = {}
                patient_updates = {}

                for item in batch:
                    first, last = split_name(item['name'])
                    phone = (item['phone'] or '')[:20]
                    name_key = normalize_name(item['name'])

                    patient_id = patient_by_phone.get(phone) if phone else None
                    if patient_id is None:
                        patient_id = patient_by_name.get(name_key)

                    patient = None
                    if patient_id:
                        # Cache values may be PKs; fetch once per unique patient
                        # for this batch, then keep the object in memory.
                        patient = row_patient.get(patient_id)
                        if patient is None:
                            patient = Patient.objects.filter(pk=patient_id).first()
                            if patient is not None:
                                row_patient[patient_id] = patient

                    if patient is None:
                        pending_key = ('phone', phone) if phone else ('name', name_key)
                        patient = next(
                            (p for k, p in pending_patients if k == pending_key),
                            None,
                        )
                        if patient is None:
                            historical_first = timezone.make_aware(
                                datetime.combine(item['date'], time.min),
                                timezone.get_current_timezone(),
                            )
                            patient = Patient(
                                first_name=first,
                                last_name=last,
                                gender=item['gender'],
                                phone=phone,
                                address=item['address'],
                                reason_for_visit=item['treatment'],
                                registered_at=historical_first,
                            )
                            pending_patients.append((pending_key, patient))
                            stats['patients_created'] += 1
                        else:
                            stats['patients_reused'] += 1
                    else:
                        stats['patients_reused'] += 1

                    # Keep the earliest historical registration date.
                    historical_first = timezone.make_aware(
                        datetime.combine(item['date'], time.min),
                        timezone.get_current_timezone(),
                    )
                    if patient.registered_at is None or historical_first < patient.registered_at:
                        patient.registered_at = historical_first
                        if patient.pk:
                            patient_updates[patient.pk] = patient

                    if patient.pk:
                        patient_by_name[name_key] = patient.pk
                        if phone:
                            patient_by_phone[phone] = patient.pk
                            if phone.startswith('+256'):
                                patient_by_phone.setdefault('0' + phone[4:], patient.pk)
                    row_patient[f'row:{item["tx_id"]}'] = patient

                if pending_patients:
                    Patient.objects.bulk_create([p for _, p in pending_patients], batch_size=len(pending_patients))
                    for pending_key, patient in pending_patients:
                        if patient.pk:
                            row_patient_key = None
                            if pending_key[0] == 'phone' and pending_key[1]:
                                patient_by_phone[pending_key[1]] = patient.pk
                                if pending_key[1].startswith('+256'):
                                    patient_by_phone.setdefault('0' + pending_key[1][4:], patient.pk)
                            patient_by_name[normalize_name(f'{patient.first_name} {patient.last_name}')] = patient.pk

                if patient_updates:
                    Patient.objects.bulk_update(
                        list(patient_updates.values()),
                        ['registered_at'],
                        batch_size=max(1, len(patient_updates)),
                    )

                # Rebuild row patient references after bulk_create assigned PKs.
                for item in batch:
                    first, last = split_name(item['name'])
                    phone = (item['phone'] or '')[:20]
                    name_key = normalize_name(item['name'])
                    patient_id = patient_by_phone.get(phone) if phone else None
                    if patient_id is None:
                        patient_id = patient_by_name.get(name_key)
                    patient = row_patient.get(f'row:{item["tx_id"]}')
                    if patient is None or not patient.pk:
                        patient = Patient.objects.get(pk=patient_id)
                        row_patient[f'row:{item["tx_id"]}'] = patient

                    changed = False
                    if item['address'] and not patient.address:
                        patient.address = item['address']; changed = True
                    if phone and not patient.phone:
                        patient.phone = phone; changed = True
                    if item['gender'] and patient.gender == 'O' and item['gender'] != 'O':
                        patient.gender = item['gender']; changed = True
                    if changed:
                        patient_updates[patient.pk] = patient

                if patient_updates:
                    Patient.objects.bulk_update(
                        list(patient_updates.values()),
                        ['address', 'phone', 'gender', 'registered_at'],
                        batch_size=max(1, len(patient_updates)),
                    )

                # ------------------------------------------------------------
                # 3) Appointments.  Existing TX markers are reused when present.
                # ------------------------------------------------------------
                existing_appts = {
                    tx: Appointment.objects.get(pk=pk)
                    for tx, pk in imported_appointments.items()
                    if any(x['tx_id'] == tx for x in batch)
                }

                # Slot counts are computed once per doctor/date pair.
                slot_keys = {(doctor_cache[x['doctor']], x['date']) for x in batch}
                for doctor_id, visit_date in slot_keys:
                    key = (doctor_id, visit_date)
                    if key not in appointment_slot_counts:
                        appointment_slot_counts[key] = Appointment.objects.filter(
                            doctor_id=doctor_id, appointment_date=visit_date
                        ).count()

                new_appointments = []
                row_appointment = {}
                for item in batch:
                    tx = item['tx_id']
                    patient = row_patient[f'row:{tx}']
                    service_name = service_for(item['treatment'])
                    service = service_cache[service_name]
                    doctor_id = doctor_cache[item['doctor']]
                    appointment = existing_appts.get(tx)

                    marker = (
                        f"Imported from corrected register: "
                        f"transaction_id={tx};"
                        f"source_row={item['row']};"
                        f"date={item['date'].isoformat()};"
                        f"treatment={item['treatment']};"
                    )

                    if not options['no_visits']:
                        if appointment is None:
                            slot_key = (doctor_id, item['date'])
                            n = appointment_slot_counts[slot_key]
                            appointment_slot_counts[slot_key] += 1
                            appointment_time = (
                                datetime.combine(item['date'], time.min) + timedelta(minutes=n)
                            ).time()
                            notes = marker + f" Original doctor: {item['doctor_raw'] or 'N/A'}."
                            if item['contact_raw'] and item['contact_raw'] != item['phone']:
                                notes += f" Original register contact: {item['contact_raw']}."
                            if item['offer']:
                                notes += f" Register status/offer: {item['offer']}."
                            appointment = Appointment(
                                patient_id=patient.pk,
                                doctor_id=doctor_id,
                                service_id=service.pk,
                                appointment_date=item['date'],
                                appointment_time=appointment_time,
                                duration_minutes=service.duration_minutes or 30,
                                status='completed',
                                notes=notes,
                                consultation_notes=item['treatment'],
                                treatment_cost=item['paid'] + item['balance'],
                                notification_phone=patient.phone or '',
                                created_by=creator,
                            )
                            new_appointments.append((tx, appointment))
                            stats['visits_created'] += 1
                        else:
                            changed = []
                            if appointment.appointment_date != item['date']:
                                appointment.appointment_date = item['date']; changed.append('appointment_date')
                            if appointment.patient_id != patient.pk:
                                appointment.patient_id = patient.pk; changed.append('patient_id')
                            if changed:
                                appointment.save(update_fields=changed)

                        row_appointment[tx] = appointment

                if new_appointments:
                    Appointment.objects.bulk_create(
                        [a for _, a in new_appointments],
                        batch_size=len(new_appointments),
                    )
                    for tx, appointment in new_appointments:
                        imported_appointments[tx] = appointment.pk
                        row_appointment[tx] = appointment

                # ------------------------------------------------------------
                # 4) Treatments, invoices, invoice items and payments in bulk.
                # ------------------------------------------------------------
                treatments = []
                invoices = []
                invoice_items = []
                payments = []

                for item in batch:
                    tx = item['tx_id']
                    patient = row_patient[f'row:{tx}']
                    service = service_cache[service_for(item['treatment'])]
                    doctor_id = doctor_cache[item['doctor']]
                    appointment = row_appointment.get(tx)
                    marker = (
                        f"Imported from corrected register: "
                        f"transaction_id={tx};"
                        f"source_row={item['row']};"
                        f"date={item['date'].isoformat()};"
                        f"treatment={item['treatment']};"
                    )

                    if not options['no_visits'] and appointment is not None:
                        treatments.append(Treatment(
                            patient_id=patient.pk,
                            doctor_id=doctor_id,
                            service_id=service.pk,
                            appointment_id=appointment.pk,
                            notes=marker + ' ' + (item['treatment'] or service.name),
                            amount=item['paid'] + item['balance'],
                        ))

                    if not options['no_billing']:
                        total_amount = item['paid'] + item['balance']
                        if total_amount > 0:
                            invoice = Invoice(
                                invoice_number=f"REG-{tx}",
                                patient_id=patient.pk,
                                appointment_id=appointment.pk if appointment is not None else None,
                                patient_name=patient.full_name,
                                patient_phone=patient.phone or '',
                                issue_date=item['date'], due_date=item['date'],
                                subtotal=total_amount, tax_rate=Decimal('0'),
                                tax_amount=Decimal('0'), discount=Decimal('0'),
                                total_amount=total_amount, amount_paid=item['paid'],
                                balance_due=item['balance'],
                                status=('paid' if item['balance'] <= 0 else ('partially_paid' if item['paid'] > 0 else 'sent')),
                                payment_method=('cash' if item['paid'] > 0 else ''),
                                notes=marker + f" Treatment: {item['treatment']}.",
                                created_by=creator.username if creator else '',
                                updated_by=creator.username if creator else '',
                            )
                            invoices.append((tx, invoice, service, total_amount, item))

                if treatments:
                    Treatment.objects.bulk_create(treatments, batch_size=len(treatments))
                    stats['treatments_created'] += len(treatments)

                if invoices:
                    Invoice.objects.bulk_create(
                        [x[1] for x in invoices], batch_size=len(invoices)
                    )
                    stats['invoices_created'] += len(invoices)
                    for tx, invoice, service, total_amount, item in invoices:
                        imported_invoices[tx] = invoice.pk
                        invoice_items.append(InvoiceItem(
                            invoice_id=invoice.pk,
                            service_id=service.pk,
                            description=item['treatment'] or service.name,
                            quantity=1,
                            unit_price=total_amount,
                            total_price=total_amount,
                        ))
                        if item['paid'] > 0:
                            payments.append(Payment(
                                invoice_id=invoice.pk,
                                amount=item['paid'],
                                payment_date=item['date'],
                                payment_method='cash',
                                status='completed',
                                notes=(
                                    f"Imported from corrected register: "
                                    f"transaction_id={tx};"
                                    f"source_row={item['row']};"
                                    f"date={item['date'].isoformat()};"
                                    f"treatment={item['treatment']};"
                                ),
                                processed_by=creator.username if creator else '',
                            ))

                if invoice_items:
                    InvoiceItem.objects.bulk_create(invoice_items, batch_size=len(invoice_items))
                if payments:
                    Payment.objects.bulk_create(payments, batch_size=len(payments))
                    stats['payments_created'] += len(payments)

            progress_done += len(batch)
            elapsed = max(_time.monotonic() - progress_started, 0.001)
            rate_per_min = progress_done / elapsed * 60
            remaining = max(total - progress_done, 0)
            eta_min = remaining / rate_per_min if rate_per_min > 0 else 0
            self.stdout.write(
                f"Progress: {progress_done}/{total} "
                f"({progress_done / total * 100:.1f}%) | "
                f"{rate_per_min:.1f} rows/min | ETA {eta_min:.1f} min"
            )

        processed = 0
        for start_idx in range(0, total, batch_size):
            batch = parsed[start_idx:start_idx + batch_size]
            last_error = None

            for attempt in range(1, 4):
                try:
                    # If a connection failure caused a retry, progress is based on
                    # the beginning of this batch so ETA remains meaningful.
                    progress_done = start_idx
                    import_batch(batch)
                    last_error = None
                    break
                except (OperationalError, InterfaceError) as exc:
                    last_error = exc
                    try:
                        connection.close()
                    except Exception:
                        pass
                    close_old_connections()
                    if attempt < 3:
                        self.stdout.write(self.style.WARNING(
                            f"Database connection lost on rows {start_idx + 1}-"
                            f"{start_idx + len(batch)}. Retrying batch ({attempt + 1}/3)..."
                        ))
                        _time.sleep(2 * attempt)

            if last_error is not None:
                raise CommandError(
                    f'Database connection failed after 3 attempts for rows '
                    f'{start_idx + 1}-{start_idx + len(batch)}: {last_error}'
                ) from last_error

            processed += len(batch)

        elapsed_total = max(_time.monotonic() - progress_started, 0.001)
        self.stdout.write(self.style.SUCCESS(
            f"Import finished: {processed}/{total} rows in "
            f"{elapsed_total/60:.1f} minutes."
        ))

        stats['rows'] = processed
        stats['warnings'] = len(warnings)

        self.stdout.write(self.style.SUCCESS(
            '\nREGISTER IMPORT COMPLETE'
        ))
        for key, value in stats.items():
            self.stdout.write(
                f'{key.replace("_", " ").title()}: {value}'
            )

        if warnings:
            self.stdout.write(self.style.WARNING(
                f'Warnings: {len(warnings)}'
            ))
            for warning in warnings[:30]:
                self.stdout.write(f'  - {warning}')
        else:
            self.stdout.write(self.style.SUCCESS('No warnings.'))
