from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db.models import Sum, Q
from patients.models import Patient
from billing.models import Invoice, Payment

class Command(BaseCommand):
    help = 'Diagnose a patient balance and register invoice/payment attachment.'

    def add_arguments(self, parser):
        parser.add_argument('search', nargs='?', default='BRANDON MUJWIGA')

    def handle(self, *args, **options):
        search = (options['search'] or '').strip()
        self.stdout.write('=' * 70)
        self.stdout.write('PATIENT BALANCE DIAGNOSTIC')
        self.stdout.write(f'Search: {search}')
        self.stdout.write('=' * 70)

        tokens = [t for t in search.split() if t]
        name_q = Q()
        for token in tokens:
            name_q &= (Q(first_name__icontains=token) | Q(last_name__icontains=token))
        qs = Patient.objects.filter(name_q).order_by('id') if tokens else Patient.objects.none()
        if not qs.exists():
            qs = Patient.objects.filter(phone__icontains=search).order_by('id')
        self.stdout.write(f'Patients found: {qs.count()}')

        for p in qs:
            invoices = Invoice.objects.filter(patient=p).order_by('issue_date', 'id')
            register = invoices.filter(invoice_number__startswith='REG-TX-')
            all_balance = invoices.aggregate(x=Sum('balance_due'))['x'] or Decimal('0')
            reg_balance = register.aggregate(x=Sum('balance_due'))['x'] or Decimal('0')
            self.stdout.write('')
            self.stdout.write(f'PATIENT ID: {p.id}')
            self.stdout.write(f'NAME: {p.first_name} {p.last_name}'.strip())
            self.stdout.write(f'PHONE: {p.phone}')
            self.stdout.write(f'ALL INVOICE BALANCE: {all_balance}')
            self.stdout.write(f'REGISTER BALANCE: {reg_balance}')
            self.stdout.write(f'INVOICE COUNT: {invoices.count()} / REGISTER: {register.count()}')
            for inv in register:
                paid = inv.payments.filter(status='completed').aggregate(x=Sum('amount'))['x'] or Decimal('0')
                self.stdout.write(
                    f'  {inv.invoice_number} | total={inv.total_amount} | amount_paid={inv.amount_paid} '
                    f'| balance_due={inv.balance_due} | status={inv.status} | payments={paid}'
                )

        self.stdout.write('')
        self.stdout.write('EXPECTED FROM REBUILT LEDGER: UGX 190,000 for Brandon Mujwiga')
