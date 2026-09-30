import re
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

import openpyxl
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Sum

from billing.models import Invoice, Payment
from patients.models import Patient

ZERO = Decimal('0.00')


def norm(value):
    return re.sub(r'\s+', ' ', str(value or '').strip()).upper()


def phone_key(value):
    if value is None:
        return ''
    raw = str(value).strip()
    if not raw:
        return ''
    digits = re.sub(r'\D', '', raw)
    if not digits:
        return ''
    if digits.startswith('256'):
        return '+' + digits
    if digits.startswith('0'):
        return '+256' + digits[1:]
    if digits.startswith('7') and len(digits) == 9:
        return '+256' + digits
    return '+' + digits


def money(value):
    if value is None or value == '':
        return ZERO
    return Decimal(str(value)).quantize(Decimal('0.01'))


def as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise ValueError(f'Invalid date value: {value!r}')


class Command(BaseCommand):
    help = (
        'Repair historical REG-TX invoices/payments from the rebuilt register ledger. '
        'Default is dry-run; use --apply to modify the database.'
    )

    def add_arguments(self, parser):
        parser.add_argument('file', help='Rebuilt register workbook (.xlsx)')
        parser.add_argument('--apply', action='store_true', help='Apply the repair to the database')
        parser.add_argument('--limit', type=int, default=0, help='Only process the first N patient keys (testing only)')
        parser.add_argument('--chunk-size', type=int, default=100, help='Patients committed per database chunk (default: 100)')
        parser.add_argument('--resume', action='store_true', help='Resume from the local checkpoint created by a previous interrupted apply')
        parser.add_argument('--repair-mismatches', action='store_true', help='Find and rebuild only patients whose current REG-TX balance differs from the verified ledger')

    def handle(self, *args, **options):
        path = options['file']
        apply = options['apply']
        limit = options['limit'] or 0
        chunk_size = max(int(options.get('chunk_size') or 100), 1)
        resume = bool(options.get('resume'))
        repair_mismatches = bool(options.get('repair_mismatches'))

        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        except Exception as exc:
            raise CommandError(f'Unable to open workbook: {exc}') from exc

        if 'TRANSACTIONS' not in wb.sheetnames or 'PATIENT_SUMMARY' not in wb.sheetnames:
            raise CommandError('Workbook must contain TRANSACTIONS and PATIENT_SUMMARY sheets.')

        rows = self._read_transactions(wb['TRANSACTIONS'])
        summaries = self._read_summary(wb['PATIENT_SUMMARY'])
        grouped = defaultdict(list)
        for row in rows:
            grouped[row['key']].append(row)

        keys = sorted(grouped.keys())
        if limit:
            keys = keys[:limit]

        self.stdout.write(self.style.MIGRATE_HEADING('REGISTER LEDGER REPAIR'))
        self.stdout.write(f'Workbook rows: {len(rows)}')
        self.stdout.write(f'Patient keys: {len(grouped)}')
        self.stdout.write(f'Mode: {"APPLY" if apply else "DRY-RUN"}')

        if not apply:
            self.stdout.write('Resolving patient keys from one database snapshot...')
            report = self._dry_run(keys, grouped, summaries)
            self._print_report(report)
            return

        report = self._apply(keys, grouped, summaries, chunk_size=chunk_size, resume=resume, repair_mismatches=repair_mismatches)
        self._print_report(report)
        if report['mismatches']:
            raise CommandError('Repair completed with reconciliation mismatches. Review the report above.')
        self.stdout.write(self.style.SUCCESS('REGISTER LEDGER REPAIR PASSED: all processed patient balances reconcile.'))

    def _read_transactions(self, sheet):
        it = sheet.iter_rows(values_only=True)
        try:
            raw_headers = next(it)
        except StopIteration:
            raise CommandError('TRANSACTIONS sheet is empty.')
        headers = [str(x or '').strip().upper() for x in raw_headers]
        idx = {h: headers.index(h) for h in headers}
        required = [
            'TRANSACTION_ID', 'SOURCE_ROW', 'DATE', 'NAMES', 'AMOUNT_PAID',
            'BALANCE', 'CONTACT', 'PREVIOUS_BALANCE', 'IMPLIED_CHARGE'
        ]
        missing = [h for h in required if h not in idx]
        if missing:
            raise CommandError(f'TRANSACTIONS is missing columns: {", ".join(missing)}')

        rows = []
        for raw in it:
            name = norm(raw[idx['NAMES']])
            if not name:
                continue
            try:
                d = as_date(raw[idx['DATE']])
            except ValueError as exc:
                raise CommandError(str(exc)) from exc
            contact = phone_key(raw[idx['CONTACT']])
            key = ('P:' + contact) if contact else ('N:' + name)
            rows.append({
                'tx': str(raw[idx['TRANSACTION_ID']] or '').strip(),
                'source_row': int(raw[idx['SOURCE_ROW']] or 0),
                'date': d,
                'name': name,
                'contact': contact,
                'paid': money(raw[idx['AMOUNT_PAID']]),
                'balance': money(raw[idx['BALANCE']]),
                'previous_balance': money(raw[idx['PREVIOUS_BALANCE']]),
                'charge': money(raw[idx['IMPLIED_CHARGE']]),
                'key': key,
            })
        return rows

    def _read_summary(self, sheet):
        it = sheet.iter_rows(values_only=True)
        try:
            raw_headers = next(it)
        except StopIteration:
            raise CommandError('PATIENT_SUMMARY sheet is empty.')
        headers = [str(x or '').strip().upper() for x in raw_headers]
        idx = {h: headers.index(h) for h in headers}
        required = ['PATIENT_KEY', 'PATIENT_NAME', 'CONTACT', 'FINAL_BALANCE']
        missing = [h for h in required if h not in idx]
        if missing:
            raise CommandError(f'PATIENT_SUMMARY is missing columns: {", ".join(missing)}')

        result = {}
        for raw in it:
            key = str(raw[idx['PATIENT_KEY']] or '').strip()
            if not key:
                continue
            result[key] = {
                'name': norm(raw[idx['PATIENT_NAME']]),
                'contact': phone_key(raw[idx['CONTACT']]),
                'expected_balance': money(raw[idx['FINAL_BALANCE']]),
            }
        return result

    def _find_patient(self, row):
        contact = row['contact']
        if contact:
            variants = [contact]
            if contact.startswith('+256'):
                variants.append('0' + contact[4:])
            patient = Patient.objects.filter(phone__in=variants).order_by('id').first()
            if patient:
                return patient

        name = row['name']
        first = name.split(' ')[0] if name else ''
        qs = Patient.objects.all()
        if first:
            qs = qs.filter(first_name__icontains=first)
        for patient in qs.order_by('id'):
            if norm(patient.full_name) == name:
                return patient
        return None

    def _patient_map(self, keys, grouped):
        """Resolve all workbook patient keys with one database read.

        The previous implementation executed a phone query for every patient and,
        when needed, scanned matching names one patient at a time. With 1,345 keys
        that created a large number of PostgreSQL round trips even during dry-run.
        Build phone/name indexes in memory instead.
        """
        patients = list(
            Patient.objects.only('id', 'first_name', 'last_name', 'phone').iterator()
        )
        by_phone = {}
        by_name = {}
        for patient in patients:
            pkey = phone_key(patient.phone)
            if pkey and pkey not in by_phone:
                by_phone[pkey] = patient
            if pkey and pkey.startswith('+256'):
                local = '0' + pkey[4:]
                if local not in by_phone:
                    by_phone[local] = patient
            nkey = norm(f'{patient.first_name} {patient.last_name}')
            if nkey and nkey not in by_name:
                by_name[nkey] = patient

        result = {}
        missing = []
        for key in keys:
            row = min(grouped[key], key=lambda x: (x['date'], x['source_row']))
            patient = by_phone.get(row['contact']) if row['contact'] else None
            if patient is None:
                patient = by_name.get(row['name'])
            if patient is None:
                missing.append(f'{key} ({row["name"]})')
            else:
                result[key] = patient
        return result, missing

    def _project_patient(self, rows):
        """Project invoices/payments chronologically using the same ledger semantics.

        Positive implied charge creates the current transaction invoice.
        Negative implied charge is a write-off against outstanding historical invoices.
        Payment on the same row is applied to that row's invoice first, then FIFO older debt.
        """
        invoices = []
        payments = []
        outstanding = []
        for row in sorted(rows, key=lambda x: (x['date'], x['source_row'])):
            current = None
            charge = max(row['charge'], ZERO)
            negative = max(-row['charge'], ZERO)

            if charge > ZERO:
                current = {
                    'tx': row['tx'], 'date': row['date'], 'total': charge,
                    'paid': ZERO, 'balance': charge,
                }
                invoices.append(current)
                outstanding.append(current)

            if negative > ZERO:
                remaining = negative
                for inv in list(outstanding):
                    if remaining <= ZERO:
                        break
                    cut = min(remaining, inv['balance'])
                    inv['total'] -= cut
                    inv['balance'] -= cut
                    remaining -= cut
                    if inv['balance'] <= ZERO:
                        if inv in outstanding:
                            outstanding.remove(inv)
                if remaining > ZERO:
                    raise ValueError(f'{row["tx"]}: write-off exceeds outstanding balance by {remaining}')

            payment_left = row['paid']
            if payment_left > ZERO:
                targets = []
                if current is not None and current['balance'] > ZERO:
                    targets.append(current)
                targets.extend(inv for inv in outstanding if inv is not current and inv['balance'] > ZERO)
                for inv in targets:
                    if payment_left <= ZERO:
                        break
                    amount = min(payment_left, inv['balance'])
                    inv['paid'] += amount
                    inv['balance'] -= amount
                    payment_left -= amount
                    payments.append((row, inv, amount))
                    if inv['balance'] <= ZERO and inv in outstanding:
                        outstanding.remove(inv)
                if payment_left > ZERO:
                    raise ValueError(f'{row["tx"]}: payment exceeds outstanding ledger balance by {payment_left}')

        final_balance = sum((inv['balance'] for inv in invoices), ZERO)
        return invoices, payments, final_balance

    def _dry_run(self, keys, grouped, summaries):
        patient_map, missing = self._patient_map(keys, grouped)
        report = {
            'checked': 0, 'matched': len(patient_map), 'missing': missing,
            'invoices': 0, 'payments': 0, 'payment_total': ZERO,
            'summary_fallbacks': 0, 'mismatches': [], 'projection_errors': [], 'patients': [],
        }
        for key in keys:
            if key not in patient_map:
                continue
            rows = grouped[key]
            try:
                invoices, payments, projected = self._project_patient(rows)
            except ValueError as exc:
                report['projection_errors'].append(f'{key}: {exc}')
                continue
            summary_row = summaries.get(key)
            if summary_row is not None:
                expected = summary_row.get('expected_balance', ZERO)
            else:
                # Some legacy phone-key patients are present in TRANSACTIONS but
                # were omitted from PATIENT_SUMMARY. The ledger's last BALANCE is
                # the authoritative expected closing balance for that patient.
                expected = sorted(rows, key=lambda x: (x['date'], x['source_row']))[-1]['balance']
                report['summary_fallbacks'] = report.get('summary_fallbacks', 0) + 1
            report['checked'] += 1
            report['invoices'] += len(invoices)
            report['payments'] += len(payments)
            report['payment_total'] += sum((p[2] for p in payments), ZERO)
            if expected is None or projected != expected:
                report['mismatches'].append(
                    f'{key}: projected {projected} != expected {expected}'
                )
            report['patients'].append((key, patient_map[key].id, expected, projected))
        return report

    def _apply(self, keys, grouped, summaries, chunk_size=100, resume=False, repair_mismatches=False):
        """Apply the validated repair in restartable chunks with progress output.

        The dry-run already proves the complete ledger projection. Apply therefore
        avoids per-payment model saves and commits a bounded number of patients at
        a time. A small local checkpoint lets an interrupted Railway connection
        resume without repeating completed patients.
        """
        patient_map, missing = self._patient_map(keys, grouped)
        report = {
            'checked': 0, 'matched': len(patient_map), 'missing': missing,
            'invoices': 0, 'payments': 0, 'payment_total': ZERO,
            'summary_fallbacks': 0, 'mismatches': [], 'projection_errors': [], 'patients': [],
        }
        if missing:
            return report

        # Project and validate everything before touching the database.
        plans = []
        for key in keys:
            patient = patient_map.get(key)
            if patient is None:
                continue
            rows = sorted(grouped[key], key=lambda x: (x['date'], x['source_row']))
            try:
                projected_invoices, projected_payments, projected_balance = self._project_patient(rows)
            except ValueError as exc:
                report['projection_errors'].append(f'{key}: {exc}')
                continue
            summary_row = summaries.get(key)
            if summary_row is not None:
                expected = summary_row.get('expected_balance', ZERO)
            else:
                expected = rows[-1]['balance']
                report['summary_fallbacks'] += 1
            if projected_balance != expected:
                report['mismatches'].append(
                    f'{key}: projected {projected_balance} != expected {expected}'
                )
                continue
            plans.append((key, patient, rows, projected_invoices, projected_payments, expected))

        if report['projection_errors'] or report['mismatches']:
            return report

        # A previous full apply can finish all chunks while leaving a small
        # number of patients whose persisted register balance does not match
        # the verified ledger. In that case, rebuild only those patients.
        # This deliberately ignores the normal checkpoint because the
        # checkpoint marks completed work, whereas these patients need a
        # targeted second pass.
        if repair_mismatches:
            # A single Django Patient can legitimately be represented by more than
            # one workbook key (for example one set of rows keyed by phone and
            # another keyed by name). Never compare or rebuild those keys as if
            # they were separate database patients. Aggregate the expected ledger
            # balance by the actual Patient.id first.
            expected_by_patient = {}
            patient_objects = {}
            grouped_plans = {}
            for key, patient, rows, projected_invoices, projected_payments, expected in plans:
                patient_objects[patient.id] = patient
                expected_by_patient[patient.id] = expected_by_patient.get(patient.id, ZERO) + Decimal(expected or ZERO)
                bucket = grouped_plans.setdefault(patient.id, {
                    'keys': [], 'rows': [], 'invoices': [], 'payments': [], 'expected': ZERO,
                })
                bucket['keys'].append(key)
                bucket['rows'].extend(rows)
                bucket['invoices'].extend(projected_invoices)
                bucket['payments'].extend(projected_payments)
                bucket['expected'] += Decimal(expected or ZERO)

            actual_rows = (
                Invoice.objects.filter(
                    patient_id__in=list(expected_by_patient),
                    invoice_number__startswith='REG-TX-'
                )
                .values('patient_id')
                .annotate(total=Sum('balance_due'))
            )
            actual_by_patient = {
                row['patient_id']: max(Decimal(row['total'] or ZERO), ZERO)
                for row in actual_rows
            }
            mismatch_ids = {
                patient_id
                for patient_id, expected in expected_by_patient.items()
                if actual_by_patient.get(patient_id, ZERO) != expected
            }

            # Collapse duplicate workbook keys that resolve to the same DB patient
            # into one rebuild plan. This prevents deleting/recreating the same
            # patient's register invoices twice in one chunk.
            merged_plans = []
            for patient_id in mismatch_ids:
                bucket = grouped_plans[patient_id]
                patient = patient_objects[patient_id]
                merged_plans.append((
                    f'PATIENT:{patient_id}',
                    patient,
                    sorted(bucket['rows'], key=lambda x: (x['date'], x['source_row'])),
                    bucket['invoices'],
                    bucket['payments'],
                    bucket['expected'],
                ))
            plans = merged_plans
            resume = False
            if mismatch_ids:
                self.stdout.write(self.style.WARNING(
                    f'TARGETED REPAIR: {len(mismatch_ids)} patients currently mismatch; '
                    f'rebuilding only those database patients from {len(grouped_plans)} matched ledger groups.'
                ))
            else:
                self.stdout.write(self.style.SUCCESS('TARGETED REPAIR: no mismatched patients found.'))

        checkpoint = None
        checkpoint_path = None
        if resume:
            from pathlib import Path
            import json
            checkpoint_path = Path('data') / 'register_ledger_repair_checkpoint.json'
            if checkpoint_path.exists():
                try:
                    checkpoint = json.loads(checkpoint_path.read_text(encoding='utf-8'))
                except Exception:
                    checkpoint = None

        completed_ids = set(checkpoint.get('completed_patient_ids', [])) if checkpoint else set()
        remaining = [p for p in plans if p[1].id not in completed_ids]
        total = len(plans)
        already = total - len(remaining)
        self.stdout.write(self.style.NOTICE(
            f'APPLY PLAN READY: {total} patients, {already} already completed, '
            f'{len(remaining)} remaining, chunk size {chunk_size}.'
        ))

        import time
        import json
        start_time = time.monotonic()
        processed = already

        for chunk_start in range(0, len(remaining), chunk_size):
            chunk = remaining[chunk_start:chunk_start + chunk_size]
            self.stdout.write(
                f'\n[APPLY] Starting patients {processed + 1}-{processed + len(chunk)} of {total}...'
            )
            self.stdout.flush()

            with transaction.atomic():
                # Rebuild ONLY historical register invoices for this chunk.
                # This deliberately avoids reusing stale invoice objects/IDs.
                chunk_patient_ids = [patient.id for _, patient, *_ in chunk]
                existing_chunk_invoices = list(
                    Invoice.objects.filter(
                        patient_id__in=chunk_patient_ids,
                        invoice_number__startswith='REG-TX-'
                    ).only('id')
                )
                existing_invoice_ids = [inv.id for inv in existing_chunk_invoices]
                if existing_invoice_ids:
                    Payment.objects.filter(invoice_id__in=existing_invoice_ids).delete()
                    Invoice.objects.filter(id__in=existing_invoice_ids).delete()

                invoice_creates = []
                desired_rows = []
                for key, patient, rows, projected_invoices, projected_payments, expected in chunk:
                    for data in projected_invoices:
                        inv = Invoice(
                            invoice_number=f'REG-{data["tx"]}',
                            patient=patient,
                            patient_name=patient.full_name,
                            patient_phone=patient.phone or '',
                            issue_date=data['date'],
                            due_date=data['date'],
                            subtotal=data['total'],
                            tax_rate=ZERO,
                            tax_amount=ZERO,
                            discount=ZERO,
                            total_amount=data['total'],
                            amount_paid=ZERO,
                            balance_due=data['total'],
                            status='sent',
                            payment_method='cash',
                            payment_date=None,
                            notes=f'Rebuilt from register transaction {data["tx"]}.',
                        )
                        invoice_creates.append(inv)
                        desired_rows.append((patient.id, f'REG-{data["tx"]}', data))

                if invoice_creates:
                    Invoice.objects.bulk_create(invoice_creates, batch_size=500)

                # Never use in-memory invoice primary keys. Fetch the rows that
                # PostgreSQL actually committed inside this transaction.
                desired_numbers = [number for _, number, _ in desired_rows]
                db_invoice_map = {}
                if desired_numbers:
                    db_invoices = Invoice.objects.filter(
                        patient_id__in=chunk_patient_ids,
                        invoice_number__in=desired_numbers,
                    ).only('id', 'patient_id', 'invoice_number')
                    db_invoice_map = {
                        (inv.patient_id, inv.invoice_number): inv
                        for inv in db_invoices
                    }

                # Every payment target must correspond to an invoice rebuilt in
                # this chunk. Zero-charge payment rows are intentionally mapped
                # to the older/open invoice selected by _project_patient().
                all_payment_objects = []
                for key, patient, rows, projected_invoices, projected_payments, expected in chunk:
                    for row, inv_data, amount in projected_payments:
                        lookup = (patient.id, f'REG-{inv_data["tx"]}')
                        inv = db_invoice_map.get(lookup)
                        if inv is None:
                            raise RuntimeError(
                                f'Invoice target missing after rebuild: patient={patient.id}, '
                                f'REG-{inv_data["tx"]}, source payment={row["tx"]}'
                            )
                        all_payment_objects.append(Payment(
                            invoice=inv,
                            amount=amount,
                            payment_date=row['date'],
                            payment_method='cash',
                            transaction_id=row['tx'],
                            reference=row['tx'],
                            status='completed',
                            notes=f'Rebuilt from register transaction {row["tx"]}.',
                        ))

                if all_payment_objects:
                    Payment.objects.bulk_create(all_payment_objects, batch_size=1000)

                # Synchronize invoice financial state in one set-oriented pass.
                # Payment rows were inserted directly, so avoid per-payment save().
                from django.db.models import Q
                payment_totals = {
                    row['invoice_id']: Decimal(row['total'] or ZERO)
                    for row in Payment.objects.filter(
                        invoice_id__in=[inv.pk for inv in db_invoice_map.values()]
                    ).values('invoice_id').annotate(total=Sum('amount'))
                }
                updated = []
                for inv in db_invoice_map.values():
                    paid = max(payment_totals.get(inv.id, ZERO), ZERO)
                    inv.amount_paid = paid
                    # total_amount is already the authoritative rebuilt charge.
                    # Re-fetching total here is unnecessary because these invoices
                    # were just created in this transaction.
                    # The in-memory value is not used for FK creation.
                # Re-read totals so the final state is based on actual DB rows.
                fresh = list(
                    Invoice.objects.filter(id__in=[inv.pk for inv in db_invoice_map.values()])
                    .only('id', 'total_amount', 'amount_paid', 'balance_due', 'status', 'payment_date')
                )
                for inv in fresh:
                    paid = max(payment_totals.get(inv.id, ZERO), ZERO)
                    inv.amount_paid = paid
                    inv.balance_due = max(Decimal(inv.total_amount or ZERO) - paid, ZERO)
                    inv.status = 'paid' if inv.balance_due <= ZERO else ('partially_paid' if paid > ZERO else 'sent')
                    inv.payment_date = None
                    updated.append(inv)
                if updated:
                    Invoice.objects.bulk_update(
                        updated,
                        ['amount_paid', 'balance_due', 'status', 'payment_date'],
                        batch_size=500,
                    )

            processed += len(chunk)
            elapsed = max(time.monotonic() - start_time, 0.001)
            rate = processed / elapsed
            eta = (total - processed) / rate if rate else 0
            self.stdout.write(self.style.SUCCESS(
                f'[APPLY] {processed}/{total} patients committed '
                f'({processed/total*100:.1f}%) | {rate:.1f} patients/s | ETA ~{eta/60:.1f} min'
            ))
            self.stdout.flush()

            if checkpoint_path is not None:
                checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                done = sorted(completed_ids.union(p[1].id for p in remaining[:chunk_start + len(chunk)]))
                checkpoint_path.write_text(
                    json.dumps({'completed_patient_ids': done, 'total': total}, indent=2),
                    encoding='utf-8'
                )

        # Rebuild report counters from the plans rather than relying on progress state.
        report['checked'] = total
        report['invoices'] = sum(len(p[3]) for p in plans)
        report['payments'] = sum(len(p[4]) for p in plans)
        report['payment_total'] = sum((amt for p in plans for _, _, amt in p[4]), ZERO)
        report['patients'] = [(p[0], p[1].id, p[5], p[5]) for p in plans]

        # Final set-based validation.
        actual_rows = (
            Invoice.objects.filter(invoice_number__startswith='REG-TX-')
            .values('patient_id').annotate(total=Sum('balance_due'))
        )
        actual_by_patient = {
            row['patient_id']: max(Decimal(row['total'] or ZERO), ZERO)
            for row in actual_rows
        }
        for key, patient, rows, projected_invoices, projected_payments, expected in plans:
            actual = actual_by_patient.get(patient.id, ZERO)
            if actual != expected:
                report['mismatches'].append(
                    f'{key} / patient {patient.id}: database register balance {actual} != expected {expected}'
                )

        if not report['mismatches'] and checkpoint_path is not None and checkpoint_path.exists():
            try:
                checkpoint_path.unlink()
            except OSError:
                pass
        return report

    def _print_report(self, report):
        self.stdout.write(f'Patients matched: {report["matched"]}')
        self.stdout.write(f'Patients checked/applied: {report["checked"]}')
        self.stdout.write(f'Historical invoices rebuilt: {report["invoices"]}')
        self.stdout.write(f'Historical payments rebuilt: {report["payments"]}')
        self.stdout.write(f'Payment total rebuilt: UGX {report["payment_total"]:,.2f}')
        self.stdout.write(f'Patients not found: {len(report["missing"])}')
        self.stdout.write(f'PATIENT_SUMMARY fallbacks: {report.get("summary_fallbacks", 0)}')
        for item in report['missing'][:30]:
            self.stdout.write(f'  - {item}')
        self.stdout.write(f'Projection errors: {len(report["projection_errors"])}')
        for item in report['projection_errors'][:30]:
            self.stdout.write(f'  - {item}')
        self.stdout.write(f'Mismatches: {len(report["mismatches"])}')
        for item in report['mismatches'][:50]:
            self.stdout.write(f'  - {item}')
