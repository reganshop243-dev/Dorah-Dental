from datetime import datetime, date, time
from pathlib import Path
import re
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from patients.models import Patient
from appointments.models import Appointment
from billing.models import Invoice, Payment
try:
    import openpyxl
except ImportError:
    openpyxl = None

MARK = re.compile(r"Imported from REGISTER\\.xlsx row (\\d+)\\.")

def txt(v):
    return "" if v is None else re.sub(r"\\s+", " ", str(v)).strip()

def reg_date(v):
    if isinstance(v, datetime):
        return date(v.year, v.day, v.month)
    if isinstance(v, date):
        return date(v.year, v.day, v.month)
    s = txt(v)
    if not s: return None
    for f in ("%d/%m/%Y", "%d-%m-%Y"):
        try: return datetime.strptime(s, f).date()
        except ValueError: pass
    m = re.fullmatch(r"(\\d{1,2})/(\\d{1,2})/(\\d{3})", s)
    if m:
        d, mo, y = map(int, m.groups())
        if y == 206:
            return date(2026, mo, d)
    return None

class Command(BaseCommand):
    help = "Repair REGISTER.xlsx dates using DD/MM/YYYY."

    def add_arguments(self, parser):
        parser.add_argument("file", nargs="?", default="REGISTER.xlsx")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--sample", type=int, default=20)

    def handle(self, *args, **opt):
        if openpyxl is None:
            raise CommandError("Install openpyxl first.")
        p = Path(opt["file"])
        if not p.exists():
            raise CommandError(f"Excel file not found: {p}")
        wb = openpyxl.load_workbook(p, data_only=False, read_only=True)
        ws = wb["daily record"]
        row_dates, active, skipped, groups = {}, None, [], 0
        for r, row in enumerate(ws.iter_rows(values_only=True), 1):
            vals = list(row) + [None] * 10
            a, name = vals[0], txt(vals[1])
            if txt(a) and all(txt(x)=="" for x in vals[1:10]):
                d = reg_date(a)
                if d: active, groups = d, groups + 1
                else: skipped.append((r, a))
                continue
            if name and active:
                row_dates[r] = active
            elif name and not active:
                skipped.append((r, "NO ACTIVE DATE"))

        appts = list(Appointment.objects.filter(notes__contains="Imported from REGISTER.xlsx row").select_related("patient"))
        expected_patient = {}
        changed_appts = changed_inv = changed_pay = changed_pat = 0
        samples = []

        for a in appts:
            m = MARK.search(a.notes or "")
            if not m: continue
            rn = int(m.group(1)); d = row_dates.get(rn)
            if not d: continue
            expected_patient[a.patient_id] = min(expected_patient.get(a.patient_id, d), d)
            if a.appointment_date != d:
                changed_appts += 1
                if len(samples) < opt["sample"]:
                    samples.append(f"Appointment row {rn}: {a.patient.full_name} | {a.appointment_date} -> {d}")
                if not opt["dry_run"]:
                    a.appointment_date = d
                    a.save(update_fields=["appointment_date"])

        for inv in Invoice.objects.filter(notes__contains="Imported from REGISTER.xlsx row"):
            m = MARK.search(inv.notes or "")
            if not m: continue
            d = row_dates.get(int(m.group(1)))
            if not d: continue
            if inv.issue_date != d or inv.due_date != d:
                changed_inv += 1
                if not opt["dry_run"]:
                    inv.issue_date = d; inv.due_date = d
                    inv.save(update_fields=["issue_date","due_date"])

        for pay in Payment.objects.filter(notes__contains="Imported from REGISTER.xlsx row"):
            m = MARK.search(pay.notes or "")
            if not m: continue
            d = row_dates.get(int(m.group(1)))
            if d and pay.payment_date != d:
                changed_pay += 1
                if not opt["dry_run"]:
                    pay.payment_date = d
                    pay.save(update_fields=["payment_date"])

        for patient in Patient.objects.filter(id__in=expected_patient):
            d = expected_patient[patient.id]
            current = patient.registered_at
            cd = timezone.localtime(current).date() if current and timezone.is_aware(current) else (current.date() if current else None)
            if cd != d:
                changed_pat += 1
                if len(samples) < opt["sample"]:
                    samples.append(f"Patient: {patient.full_name} | {cd} -> {d}")
                if not opt["dry_run"]:
                    patient.registered_at = timezone.make_aware(datetime.combine(d, time.min), timezone.get_current_timezone())
                    patient.save(update_fields=["registered_at"])

        self.stdout.write(self.style.SUCCESS("REGISTER DATE REPAIR REPORT"))
        self.stdout.write(f"Date groups: {groups}")
        self.stdout.write(f"Mapped historical rows: {len(row_dates)}")
        self.stdout.write(f"Appointments to repair: {changed_appts}")
        self.stdout.write(f"Invoices to repair: {changed_inv}")
        self.stdout.write(f"Payments to repair: {changed_pay}")
        self.stdout.write(f"Patients to repair: {changed_pat}")
        self.stdout.write("")
        self.stdout.write("SAMPLE CHANGES")
        for s in samples: self.stdout.write(s)
        if skipped:
            self.stdout.write("")
            self.stdout.write(f"Skipped rows: {len(skipped)}")
            for x in skipped[:10]: self.stdout.write(str(x))
        if opt["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY RUN ONLY - DATABASE NOT CHANGED"))
        else:
            self.stdout.write(self.style.SUCCESS("DATE REPAIR COMPLETE"))
