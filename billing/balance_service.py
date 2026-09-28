"""Canonical patient outstanding-balance calculations.

Register imports store the register's cumulative outstanding balance on each
transaction row. Those historical snapshots must not be added together.
Normal invoices remain independent and their outstanding balances are summed.
"""
from decimal import Decimal
from django.db.models import Q, Sum
from .models import Invoice

ZERO = Decimal("0.00")


def is_register_invoice_q():
    return Q(invoice_number__startswith="REG-") | Q(notes__icontains="Imported from corrected register:")


def get_patient_outstanding_balance(patient):
    """Return the current outstanding balance for a patient.

    Imported register invoices: use the latest recorded balance snapshot.
    Normal invoices: sum their individual positive balances.
    """
    invoices = Invoice.objects.filter(patient=patient)
    imported = invoices.filter(is_register_invoice_q()).order_by("-issue_date", "-id")
    latest_import = imported.first()

    imported_balance = ZERO
    if latest_import:
        imported_balance = max(Decimal(latest_import.balance_due or 0), ZERO)

    normal_balance = invoices.exclude(is_register_invoice_q()).aggregate(
        total=Sum("balance_due")
    )["total"] or ZERO

    return imported_balance + max(Decimal(normal_balance), ZERO)


def get_patient_balance_breakdown(patient):
    invoices = Invoice.objects.filter(patient=patient)
    imported = invoices.filter(is_register_invoice_q()).order_by("-issue_date", "-id")
    latest_import = imported.first()
    imported_balance = max(Decimal(latest_import.balance_due or 0), ZERO) if latest_import else ZERO
    normal_balance = invoices.exclude(is_register_invoice_q()).aggregate(
        total=Sum("balance_due")
    )["total"] or ZERO
    normal_balance = max(Decimal(normal_balance), ZERO)
    return {
        "imported_register_balance": imported_balance,
        "normal_invoice_balance": normal_balance,
        "total_balance": imported_balance + normal_balance,
        "latest_register_invoice_id": latest_import.id if latest_import else None,
    }
