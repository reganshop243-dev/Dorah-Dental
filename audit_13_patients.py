import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dental_clinic.settings")
django.setup()

from patients.models import Patient
from billing.models import Invoice

names = {
    "ABAHO SIMON",
    "AJUNA WENDY",
    "ANGELLA ROBERTS",
    "EDRISIAH KARL",
    "KAMPANE OPHELEA",
    "KAYITESI MELLAN",
    "KUMUKUNDWA FAITH",
    "LUKUNDA SUSAN",
    "MARK MORRIS SSEBAGGALA AND SEKYANZI MICHEAL",
    "MUTESI MARIAM",
    "NAMUYIGA MELLISA",
    "NIKITA",
    "SSEBAGGALA MARK MORRIS",
}

print("=" * 100)
print("13-PATIENT INVOICE AUDIT")
print("=" * 100)

found = set()

for patient in Patient.objects.all():

    patient_name = patient.full_name.upper().strip()

    if patient_name not in names:
        continue

    found.add(patient_name)

    print()
    print("=" * 100)
    print(patient.full_name)
    print("=" * 100)

    invoices = (
        Invoice.objects
        .filter(patient=patient)
        .order_by("issue_date", "id")
    )

    for invoice in invoices:
        print(
            f"{invoice.invoice_number} | "
            f"{invoice.issue_date} | "
            f"TOTAL={invoice.total_amount} | "
            f"PAID={invoice.amount_paid} | "
            f"BAL={invoice.balance_due} | "
            f"STATUS={invoice.status}"
        )

print()
print("=" * 100)
print("NOT FOUND AS DATABASE PATIENT")
print("=" * 100)

for name in sorted(names - found):
    print(name)

print()
print("=" * 100)
print("READ-ONLY AUDIT — NO CHANGES MADE")
print("=" * 100)