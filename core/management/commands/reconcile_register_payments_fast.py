from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from pathlib import Path
import re
import time as _time

from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections, connection, transaction
from django.db.utils import OperationalError, InterfaceError
from django.db.models import Sum

from patients.models import Patient
from billing.models import Invoice, InvoiceItem, Payment

try:
    import openpyxl
except ImportError:
    openpyxl = None


def clean_text(value):
    if value is None:
        return ''
    return re.sub(r'\s+', ' ', str(value)).strip()


def normalize_name(value):
    return clean_text(value).upper()


def clean_phone(value):
    raw = clean_text(value)
    if not raw:
        return ''
    first = re.sub(r'\D', '', re.split(r'[/,;]|\s+and\s+', raw, flags=re.I)[0])
    if first.startswith('256'):
        return '+' + first
    if first.startswith('0') and len(first) >= 9:
        return '+256' + first[1:]
    if first.startswith('7') and len(first) >= 9:
        return '+256' + first
    return first


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


def parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = clean_text(value)
    for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y'):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def tx_from_notes(notes):
    m = re.search(r'transaction_id=(TX-\d+)', notes or '')
    return m.group(1) if m else None


class Command(BaseCommand):
    help = (
        "Fast, resumable reconciliation of register payments after the "
        "historical register import."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'file',
            nargs='?',
            default='Dorah_Dental_REGISTER_LATEST_SHARED_PHONE_SAFE.xlsx',
        )
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--batch-size', type=int, default=250)

    def handle(self, *args, **options):
        if openpyxl is None:
            raise CommandError(
                'openpyxl is required. Install it with: python -m pip install openpyxl'
            )

        source = Path(options['file']).expanduser()
        if not source.exists():
            raise CommandError(f'Excel file not found: {source}')

        self.stdout.write(self.style.NOTICE(
            f'Loading register for FAST PAYMENT RECONCILIATION: {source}'
        ))

        wb = openpyxl.load_workbook(source, data_only=True, read_only=True)
        if 'TRANSACTIONS' not in wb.sheetnames:
            raise CommandError("Workbook must contain a TRANSACTIONS sheet.")

        ws = wb['TRANSACTIONS']
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            raise CommandError('TRANSACTIONS sheet is empty.')

        headers = [clean_text(x).upper() for x in rows[0]]
        required = [
            'TRANSACTION_ID', 'SOURCE_ROW', 'DATE', 'NAMES',
            'AMOUNT_PAID', 'BALANCE', 'CONTACT',
            'PREVIOUS_BALANCE', 'IMPLIED_CHARGE',
        ]
        missing = [x for x in required if x not in headers]
        if missing:
            raise CommandError(
                'Workbook is missing required columns: ' + ', '.join(missing)
            )
        idx = {h: headers.index(h) for h in required}

        ledger = []
        for excel_row, row in enumerate(rows[1:], start=2):
            values = list(row)
            tx = clean_text(values[idx['TRANSACTION_ID']])
            name = clean_text(values[idx['NAMES']])
            d = parse_date(values[idx['DATE']])
            if not tx or not name or d is None:
                continue
            ledger.append({
                'tx_id': tx,
                'row': int(values[idx['SOURCE_ROW']] or excel_row),
                'date': d,
                'name': name,
                'phone': clean_phone(values[idx['CONTACT']]),
                'paid': parse_money(values[idx['AMOUNT_PAID']]),
                'balance': parse_money(values[idx['BALANCE']]),
                'previous_balance': parse_money(values[idx['PREVIOUS_BALANCE']]),
                'implied_charge': parse_money(values[idx['IMPLIED_CHARGE']]),
            })

        if not ledger:
            raise CommandError('No valid ledger transactions found.')

        try:
            close_old_connections()
            connection.ensure_connection()
        except (OperationalError, InterfaceError) as exc:
            raise CommandError(
                f'PostgreSQL is not reachable. No reconciliation performed. {exc}'
            ) from exc

        # Patient identity: EXACT NAME FIRST, phone ONLY as fallback.
        name_to_patient = {}
        phone_to_patient = {}
        for p in Patient.objects.all().only('id', 'first_name', 'last_name', 'phone'):
            key = normalize_name(f'{p.first_name} {p.last_name}')
            name_to_patient.setdefault(key, p.pk)
            if p.phone:
                phone_to_patient.setdefault(p.phone, p.pk)
                if p.phone.startswith('+256'):
                    phone_to_patient.setdefault('0' + p.phone[4:], p.pk)

        # Register invoices already imported by the main importer.
        invoices = list(
            Invoice.objects.filter(
                invoice_number__startswith='REG-TX-'
            ).only(
                'id', 'invoice_number', 'patient_id', 'subtotal',
                'total_amount', 'amount_paid', 'balance_due',
                'status', 'payment_date', 'notes'
            ).order_by('issue_date', 'id')
        )
        invoice_by_tx = {}
        for inv in invoices:
            tx = inv.invoice_number[4:] if inv.invoice_number.startswith('REG-') else None
            if tx:
                invoice_by_tx[tx] = inv

        invoice_items_by_invoice = {
            item.invoice_id: item
            for item in InvoiceItem.objects.filter(
                invoice_id__in=[inv.pk for inv in invoices]
            ).only('id', 'invoice_id', 'unit_price', 'total_price')
        }

        missing_invoices = [
            x['tx_id'] for x in ledger
            if x['implied_charge'] > 0 and x['tx_id'] not in invoice_by_tx
        ]
        if missing_invoices:
            raise CommandError(
                f'{len(missing_invoices)} charge transactions have no REG invoice. '
                f'Example: {missing_invoices[:10]}. Do not modify anything; '
                f'the main import must be completed first.'
            )

        # Build patient ledger in chronological order.
        from collections import defaultdict
        rows_by_patient = defaultdict(list)
        for item in ledger:
            pid = name_to_patient.get(normalize_name(item['name']))
            if pid is None and item['phone']:
                pid = phone_to_patient.get(item['phone'])
            if pid is not None:
                rows_by_patient[pid].append(item)

        # Existing register payments are loaded ONCE. This is the key performance
        # fix: no aggregate query is performed for every invoice/payment.
        existing_register_payments = list(
            Payment.objects.filter(
                notes__contains='transaction_id=TX-'
            ).values('id', 'invoice_id', 'amount', 'status', 'notes')
        )
        existing_by_tx = defaultdict(Decimal)
        existing_by_invoice = defaultdict(Decimal)
        for p in existing_register_payments:
            tx = tx_from_notes(p['notes'])
            if not tx or p['status'] != 'completed':
                continue
            amount = Decimal(p['amount'] or 0)
            existing_by_tx[tx] += amount
            existing_by_invoice[p['invoice_id']] += amount

        self.stdout.write(self.style.SUCCESS(
            f'Loaded {len(invoices)} register invoices and '
            f'{len(existing_register_payments)} existing register payments in bulk.'
        ))

        # Rebuild invoice totals deterministically from workbook charges.
        # This makes the command safe to rerun after a partial reconciliation.
        invoice_totals = {}
        for item in ledger:
            if item['implied_charge'] > 0:
                inv = invoice_by_tx.get(item['tx_id'])
                if inv:
                    invoice_totals[inv.pk] = item['implied_charge']

        # Apply negative implied charges/write-offs FIFO by patient.
        adjustments = 0
        warnings = []
        invoice_lists = defaultdict(list)
        for item in ledger:
            inv = invoice_by_tx.get(item['tx_id'])
            if inv and item['implied_charge'] > 0:
                invoice_lists[
                    name_to_patient.get(normalize_name(item['name']))
                    or phone_to_patient.get(item['phone'])
                ].append(inv)

        for pid in invoice_lists:
            invoice_lists[pid].sort(key=lambda x: (x.issue_date, x.id))

        for pid, patient_rows in rows_by_patient.items():
            invs = invoice_lists.get(pid, [])
            if not invs:
                continue
            for item in sorted(patient_rows, key=lambda x: (x['date'], x['row'])):
                adjustment = max(-item['implied_charge'], Decimal('0'))
                if adjustment <= 0:
                    continue
                remaining = adjustment
                for inv in invs:
                    if remaining <= 0:
                        break
                    current = invoice_totals.get(inv.pk, Decimal('0'))
                    if current <= 0:
                        continue
                    reduction = min(remaining, current)
                    invoice_totals[inv.pk] = current - reduction
                    remaining -= reduction
                    adjustments += 1
                if remaining > Decimal('0.01'):
                    warnings.append(
                        f"{item['tx_id']}: write-off {adjustment} exceeded "
                        f"available invoice charges by {remaining}."
                    )

        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(
                f'DRY RUN: {len(invoice_totals)} invoice totals reconstructed; '
                f'{adjustments} write-off allocations calculated; '
                f'{len(existing_register_payments)} register payments already exist.'
            ))
            if warnings:
                self.stdout.write(self.style.WARNING(
                    f'Warnings: {len(warnings)}'
                ))
                for w in warnings[:20]:
                    self.stdout.write(f'  - {w}')
            else:
                self.stdout.write(self.style.SUCCESS('No warnings.'))
            return

        # ------------------------------------------------------------
        # Visible progress: reconciliation can take time on Railway.
        # ------------------------------------------------------------
        import time as _time
        progress_clock = _time.monotonic()

        def show_progress(label, done, total):
            total = max(int(total), 1)
            done = min(max(int(done), 0), total)
            elapsed = max(_time.monotonic() - progress_clock, 0.001)
            rate = done / elapsed * 60
            remaining = max(total - done, 0)
            eta = remaining / rate if rate > 0 else 0
            self.stdout.write(
                f"{label}: {done}/{total} "
                f"({done / total * 100:.1f}%) | "
                f"{rate:.1f}/min | ETA {eta:.1f} min"
            )

        self.stdout.write(self.style.NOTICE(
            "Starting fast reconciliation — existing data will be preserved."
        ))

        # Persist reconstructed invoice totals in one batch.
        invoice_objects = []
        for inv in invoices:
            if inv.pk not in invoice_totals:
                continue
            total = max(invoice_totals[inv.pk], Decimal('0'))
            inv.subtotal = total
            inv.total_amount = total
            inv.discount = Decimal('0')
            inv.tax_amount = Decimal('0')
            inv.balance_due = total
            inv.amount_paid = Decimal('0')
            inv.status = 'sent'
            inv.payment_date = None
            invoice_objects.append(inv)

            item_obj = invoice_items_by_invoice.get(inv.pk)
            if item_obj is not None:
                item_obj.unit_price = total
                item_obj.total_price = total

        item_updates = list(invoice_items_by_invoice.values())
        item_total = len(item_updates)
        for start in range(0, item_total, options['batch_size']):
            InvoiceItem.objects.bulk_update(
                item_updates[start:start + options['batch_size']],
                ['unit_price', 'total_price'],
                batch_size=options['batch_size'],
            )
            show_progress(
                "Invoice items",
                min(start + options['batch_size'], item_total),
                item_total,
            )

        invoice_total = len(invoice_objects)
        for start in range(0, invoice_total, options['batch_size']):
            try:
                with transaction.atomic():
                    Invoice.objects.bulk_update(
                        invoice_objects[start:start + options['batch_size']],
                        ['subtotal', 'total_amount', 'discount', 'tax_amount',
                         'balance_due', 'amount_paid', 'status', 'payment_date'],
                        batch_size=options['batch_size'],
                    )
                show_progress(
                    "Invoice totals",
                    min(start + options['batch_size'], invoice_total),
                    invoice_total,
                )
            except (OperationalError, InterfaceError) as exc:
                close_old_connections()
                raise CommandError(
                    'Database connection lost while rebuilding invoice totals. '
                    'No reset is required; rerun this FAST command.'
                ) from exc

        # Re-read payment allocation state after the invoice totals reset.
        # Existing payments are retained, and only the missing amount for each
        # transaction is created. Therefore this is genuinely resume-safe.
        payments_to_create = []
        invoice_paid = defaultdict(Decimal)

        # Include existing completed register payments.
        for invoice_id, amount in existing_by_invoice.items():
            invoice_paid[invoice_id] += amount

        # Allocate each source payment FIFO across the patient's invoices.
        patient_total = len(rows_by_patient)
        patient_done = 0
        show_progress("Payment allocation planning", 0, patient_total)
        for pid, patient_rows in rows_by_patient.items():
            invs = invoice_lists.get(pid, [])
            if not invs:
                continue

            for item in sorted(patient_rows, key=lambda x: (x['date'], x['row'])):
                source_paid = Decimal(item['paid'] or 0)
                already_allocated = existing_by_tx.get(item['tx_id'], Decimal('0'))
                remaining = max(source_paid - already_allocated, Decimal('0'))
                if remaining <= 0:
                    continue

                for inv in invs:
                    if remaining <= 0:
                        break
                    total = invoice_totals.get(inv.pk, Decimal('0'))
                    due = max(total - invoice_paid[inv.pk], Decimal('0'))
                    if due <= 0:
                        continue
                    amount = min(remaining, due)
                    if amount <= 0:
                        continue
                    marker = (
                        f"Imported from rebuilt register: "
                        f"transaction_id={item['tx_id']};"
                        f"source_row={item['row']};date={item['date'].isoformat()};"
                    )
                    payments_to_create.append(Payment(
                        invoice_id=inv.pk,
                        amount=amount,
                        payment_date=item['date'],
                        payment_method='cash',
                        status='completed',
                        notes=marker + ' Register payment reconciliation.',
                        processed_by='',
                    ))
                    invoice_paid[inv.pk] += amount
                    remaining -= amount

            patient_done += 1
            if patient_done == patient_total or patient_done % 25 == 0:
                show_progress(
                    "Payment allocation planning",
                    patient_done,
                    patient_total,
                )

        self.stdout.write(
            f'Payments still to create: {len(payments_to_create)} '
            f'(existing register payments are preserved).'
        )

        created = 0
        batch_size = max(50, int(options['batch_size']))
        for start in range(0, len(payments_to_create), batch_size):
            batch = payments_to_create[start:start + batch_size]
            for attempt in range(1, 4):
                try:
                    with transaction.atomic():
                        Payment.objects.bulk_create(batch, batch_size=batch_size)
                    created += len(batch)
                    show_progress(
                        "Payment creation",
                        created,
                        len(payments_to_create),
                    )
                    break
                except (OperationalError, InterfaceError) as exc:
                    close_old_connections()
                    if attempt == 3:
                        raise CommandError(
                            'Railway connection was lost during payment creation. '
                            'Already committed payment batches are safe. '
                            'Run this same FAST command again to resume.'
                        ) from exc
                    _time.sleep(attempt * 2)

        # Final state update using ONE grouped query, not one aggregate per invoice.
        self.stdout.write(self.style.NOTICE(
            "Calculating final invoice balances from grouped payments..."
        ))
        paid_totals = dict(
            Payment.objects.filter(
                invoice_id__in=list(invoice_totals.keys()),
                status='completed'
            ).values('invoice_id').annotate(total=Sum('amount')).values_list(
                'invoice_id', 'total'
            )
        )

        updates = []
        today = date.today()
        for inv in invoice_objects:
            total = invoice_totals.get(inv.pk, Decimal('0'))
            paid = Decimal(paid_totals.get(inv.pk, 0) or 0)
            balance = max(total - paid, Decimal('0'))
            inv.amount_paid = paid
            inv.balance_due = balance
            if total > 0 and balance <= 0:
                inv.status = 'paid'
                if not inv.payment_date:
                    inv.payment_date = today
            elif paid > 0:
                inv.status = 'partially_paid'
                inv.payment_date = None
            else:
                inv.status = 'sent'
                inv.payment_date = None
            updates.append(inv)

        final_total = len(updates)
        for start in range(0, final_total, batch_size):
            Invoice.objects.bulk_update(
                updates[start:start + batch_size],
                ['amount_paid', 'balance_due', 'status', 'payment_date'],
                batch_size=batch_size,
            )
            show_progress(
                "Final invoice states",
                min(start + batch_size, final_total),
                final_total,
            )

        self.stdout.write(self.style.SUCCESS(
            '\nFAST REGISTER PAYMENT RECONCILIATION COMPLETE'
        ))
        self.stdout.write(f'Invoices reconstructed: {len(invoice_totals)}')
        self.stdout.write(f'Payments newly created: {created}')
        self.stdout.write(f'Existing register payments preserved: {len(existing_register_payments)}')
        self.stdout.write(f'Write-off allocations: {adjustments}')
        if warnings:
            self.stdout.write(self.style.WARNING(
                f'Warnings: {len(warnings)}'
            ))
            for w in warnings[:30]:
                self.stdout.write(f'  - {w}')
        else:
            self.stdout.write(self.style.SUCCESS('No warnings.'))
