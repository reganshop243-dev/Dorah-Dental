"""
Recompute revenue and balance figures directly from source data
so you can compare them to what your reports display.

Run:
    python manage.py verify_reports
    python manage.py verify_reports --start 2026-01-01 --end 2026-12-31
"""

from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db.models import Sum, Q


class Command(BaseCommand):
    help = "Recompute revenue and balance sheet numbers for verification."

    def add_arguments(self, parser):
        parser.add_argument('--start', type=str, default=None,
                            help='Start date YYYY-MM-DD (default: beginning of this year)')
        parser.add_argument('--end', type=str, default=None,
                            help='End date YYYY-MM-DD (default: today)')

    def handle(self, *args, **options):
        from billing.models import Invoice, Payment, Expense

        today = date.today()
        start = (date.fromisoformat(options['start'])
                 if options['start'] else today.replace(month=1, day=1))
        end = (date.fromisoformat(options['end'])
               if options['end'] else today)

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\nReport verification — {start} to {end}\n" + "=" * 60
        ))

        # ---------- REVENUE ----------
        payments_total = Payment.objects.filter(
            status='completed',
            payment_date__gte=start,
            payment_date__lte=end,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        invoices_issued = Invoice.objects.filter(
            issue_date__gte=start,
            issue_date__lte=end,
        ).exclude(status__in=['cancelled', 'void']).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0')

        self.stdout.write(self.style.MIGRATE_LABEL('\nREVENUE (cash basis)'))
        self.stdout.write(f"  Payments received (completed): UGX {payments_total:,.2f}")
        self.stdout.write(f"  Invoices issued (accrual):     UGX {invoices_issued:,.2f}")

        # by method
        by_method = Payment.objects.filter(
            status='completed',
            payment_date__gte=start,
            payment_date__lte=end,
        ).values('payment_method').annotate(total=Sum('amount'))
        self.stdout.write("\n  Breakdown by method:")
        for row in by_method:
            self.stdout.write(f"    {row['payment_method'] or '(none)':<20} UGX {row['total']:>12,.2f}")

        # ---------- EXPENSES ----------
        expenses_total = Expense.objects.filter(
            expense_date__gte=start,
            expense_date__lte=end,
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        self.stdout.write(self.style.MIGRATE_LABEL('\nEXPENSES'))
        self.stdout.write(f"  Expenses (by expense_date):   UGX {expenses_total:,.2f}")

        by_cat = Expense.objects.filter(
            expense_date__gte=start,
            expense_date__lte=end,
        ).values('category').annotate(total=Sum('amount'))
        self.stdout.write("\n  Breakdown by category:")
        for row in by_cat:
            self.stdout.write(f"    {row['category'] or '(none)':<20} UGX {row['total']:>12,.2f}")

        # ---------- NET ----------
        self.stdout.write(self.style.MIGRATE_LABEL('\nNET (cash basis)'))
        self.stdout.write(f"  Revenue - Expenses:           UGX {payments_total - expenses_total:,.2f}")

        # ---------- BALANCE SHEET ----------
        total_invoiced = Invoice.objects.exclude(
            status__in=['cancelled', 'void']
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        total_paid = Payment.objects.filter(
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        outstanding = total_invoiced - total_paid

        self.stdout.write(self.style.MIGRATE_LABEL('\nBALANCE SHEET SNAPSHOT (all-time)'))
        self.stdout.write(f"  Total invoiced (excluding cancelled/void): UGX {total_invoiced:,.2f}")
        self.stdout.write(f"  Total payments received:                    UGX {total_paid:,.2f}")
        self.stdout.write(f"  Outstanding receivable:                     UGX {outstanding:,.2f}")

        # Cross-check against balance_service if available
        try:
            from billing.balance_service import get_patient_outstanding_balance
            from patients.models import Patient
            patient_sum = sum(
                (get_patient_outstanding_balance(p) for p in Patient.objects.filter(is_active=True)),
                Decimal('0'),
            )
            self.stdout.write(
                f"\n  Sum of per-patient outstanding:             UGX {patient_sum:,.2f}"
            )
            diff = outstanding - patient_sum
            if abs(diff) < Decimal('1.00'):
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Per-patient balances match the aggregate."
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"  ⚠ Difference of UGX {diff:,.2f} — investigate."
                ))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  (Could not cross-check: {e})"))

        self.stdout.write("\n")