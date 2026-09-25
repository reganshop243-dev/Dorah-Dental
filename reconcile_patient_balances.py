import os
import django
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dental_clinic.settings")
django.setup()

from openpyxl import load_workbook
from django.db.models import Sum
from patients.models import Patient
from billing.models import Invoice, Payment


EXCEL_FILE = "Dorah_Dental_Register_DMY_FINAL.xlsx"


def money(value):
    if value is None:
        return Decimal("0")
    text = str(value).strip().replace(",", "")
    if text.upper() in ("", "NIL", "NONE", "NULL", "-"):
        return Decimal("0")
    try:
        return Decimal(text)
    except Exception:
        return Decimal("0")


def normalize_name(value):
    return " ".join(str(value or "").upper().split())


# ============================================================
# LOAD EXCEL
# ============================================================
print("=" * 100)
print("READ-ONLY PATIENT BALANCE RECONCILIATION")
print("=" * 100)

wb = load_workbook(EXCEL_FILE, data_only=True)
ws = wb["TRANSACTIONS"]

headers = {}
for c in range(1, ws.max_column + 1):
    value = ws.cell(1, c).value
    if value:
        headers[str(value).strip().upper()] = c

required = [
    "TRANSACTION_ID",
    "DATE",
    "NAMES",
    "AMOUNT_PAID",
    "BALANCE",
]

for field in required:
    if field not in headers:
        raise RuntimeError(f"Missing Excel column: {field}")


# ============================================================
# GROUP EXCEL TRANSACTIONS BY PATIENT
# ============================================================
excel_patients = {}

for r in range(2, ws.max_row + 1):
    tx = ws.cell(r, headers["TRANSACTION_ID"]).value

    if not tx:
        continue

    name = normalize_name(ws.cell(r, headers["NAMES"]).value)

    if not name:
        continue

    date_value = ws.cell(r, headers["DATE"]).value
    paid = money(ws.cell(r, headers["AMOUNT_PAID"]).value)
    row_balance = money(ws.cell(r, headers["BALANCE"]).value)

    if name not in excel_patients:
        excel_patients[name] = []

    excel_patients[name].append({
        "row": r,
        "tx": str(tx).strip(),
        "date": date_value,
        "paid": paid,
        "balance": row_balance,
        "charge": paid + row_balance,
    })


# ============================================================
# LOAD PATIENTS
# ============================================================
patients = list(
    Patient.objects.all().only(
        "id",
        "first_name",
        "last_name",
        "phone",
    )
)

print(f"Excel patient groups : {len(excel_patients):,}")
print(f"Database patients    : {len(patients):,}")


# ============================================================
# DATABASE PATIENT MAP
# ============================================================
db_by_name = {}

for p in patients:
    name = normalize_name(
        f"{p.first_name or ''} {p.last_name or ''}"
    )

    if name:
        db_by_name.setdefault(name, []).append(p)


# ============================================================
# CHRONOLOGICAL BALANCE CALCULATION
# ============================================================
results = []
not_found = []

for name, transactions in excel_patients.items():

    transactions.sort(
        key=lambda x: (
            x["date"] if x["date"] else "",
            x["row"]
        )
    )

    # The Excel register's current balance is the balance
    # recorded on the latest transaction.
    excel_current_balance = (
        transactions[-1]["balance"]
        if transactions
        else Decimal("0")
    )

    # --------------------------------------------------------
    # Chronological reconciliation
    #
    # Existing debt is carried forward.
    # New payments first settle previous outstanding debt.
    # --------------------------------------------------------
    chronological_balance = Decimal("0")

    for tx in transactions:
        charge = tx["charge"]
        payment = tx["paid"]

        chronological_balance += charge

        if payment > 0:
            chronological_balance -= payment

        if chronological_balance < 0:
            chronological_balance = Decimal("0")

    # --------------------------------------------------------
    # Find database patient
    # --------------------------------------------------------
    matches = db_by_name.get(name, [])

    if not matches:
        not_found.append(name)
        continue

    patient = matches[0]

    # --------------------------------------------------------
    # Current database invoice-sum balance
    # --------------------------------------------------------
    invoice_balance = (
        Invoice.objects
        .filter(patient=patient)
        .aggregate(total=Sum("balance_due"))
        ["total"]
        or Decimal("0")
    )

    # --------------------------------------------------------
    # Completed payment total
    # --------------------------------------------------------
    completed_paid = (
        Payment.objects
        .filter(
            invoice__patient=patient,
            status="completed",
        )
        .aggregate(total=Sum("amount"))
        ["total"]
        or Decimal("0")
    )

    # --------------------------------------------------------
    # Total invoice value
    # --------------------------------------------------------
    invoice_total = (
        Invoice.objects
        .filter(patient=patient)
        .aggregate(total=Sum("total_amount"))
        ["total"]
        or Decimal("0")
    )

    accounting_balance = invoice_total - completed_paid

    if accounting_balance < 0:
        accounting_balance = Decimal("0")

    # --------------------------------------------------------
    # Difference against Excel latest balance
    # --------------------------------------------------------
    difference = (
        excel_current_balance -
        invoice_balance
    )

    # Flag if any meaningful difference exists
    if (
        excel_current_balance != invoice_balance
        or excel_current_balance != chronological_balance
        or invoice_balance != chronological_balance
    ):
        results.append({
            "name": name,
            "visits": len(transactions),
            "excel_current": excel_current_balance,
            "invoice_sum": invoice_balance,
            "chronological": chronological_balance,
            "accounting": accounting_balance,
            "difference": difference,
            "total_invoice": invoice_total,
            "completed_paid": completed_paid,
        })


# ============================================================
# OUTPUT
# ============================================================
print()
print("=" * 100)
print("RECONCILIATION SUMMARY")
print("=" * 100)

print(f"Flagged patients : {len(results):,}")
print(f"Excel patients not found in DB : {len(not_found):,}")

print()
print(
    "NAME".ljust(38),
    "VISITS".rjust(6),
    "EXCEL".rjust(14),
    "DB SUM".rjust(14),
    "CHRONO".rjust(14),
    "ACCOUNT".rjust(14),
)

print("-" * 100)

for x in results:
    print(
        x["name"][:38].ljust(38),
        str(x["visits"]).rjust(6),
        f"{x['excel_current']:,.0f}".rjust(14),
        f"{x['invoice_sum']:,.0f}".rjust(14),
        f"{x['chronological']:,.0f}".rjust(14),
        f"{x['accounting']:,.0f}".rjust(14),
    )

# ============================================================
# PATIENTS NOT FOUND
# ============================================================
if not_found:
    print()
    print("=" * 100)
    print("PATIENTS NOT FOUND IN DATABASE")
    print("=" * 100)

    for name in sorted(not_found):
        print(name)

# ============================================================
# KAYE SPECIFIC CHECK
# ============================================================
print()
print("=" * 100)
print("KAYE IBRAHIM CHECK")
print("=" * 100)

for x in results:
    if x["name"] == "KAYE IBRAHIM":
        print(x)

print()
print("=" * 100)
print("NO DATABASE CHANGES WERE MADE")
print("=" * 100)