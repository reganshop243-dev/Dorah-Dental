from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from openpyxl import load_workbook

from billing.models import Expense


CATEGORY_MAP = {
    "DISPOSABLES": "supplies",
    "MASKS": "supplies",
    "MATERIALS": "supplies",
    "LIQUID SOAP": "supplies",
    "CABLE": "supplies",
    "ELECTRICITY": "utilities",
    "TRANSPORT": "travel",
    "CONTENT CREATOR": "marketing",
    "LABOUR": "maintenance",
    "PLUMBERS": "maintenance",
    "FOOD": "other",
    "ALLOWANCE": "other",
    "DORA": "other",
    "JOLLY": "other",
    "ONER BERRIES": "other",
    "BOOKS": "other",
    "TOILET": "other",
    "EXPENSES": "other",
    "EXTRA": "other",
    "REFUND(RCT)": "other",
}


def clean_text(value):
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def parse_source_date(value):
    """
    Source workbook uses DD/MM/YYYY, but Excel stored some early dates
    as real date cells interpreted as MM/DD/YYYY.

    Example:
      Excel 2026-01-07 -> source 01/07/2026
      Excel 2026-06-08 -> source 06/08/2026
      Excel 2026-07-06 -> source 07/06/2026

    Therefore real datetime cells are interpreted by swapping month/day.
    Text dates are parsed directly as DD/MM/YYYY.
    """
    if isinstance(value, datetime):
        # The first date blocks in this workbook were entered as dates such
        # as 1/7/2026, 2/7/2026 ... but Excel interpreted them as
        # January 7, February 7, etc. The intended source format is
        # DD/MM/YYYY, and those first blocks are July, August and September.
        #
        # For these real Excel date cells, use the Excel MONTH as the
        # intended day and the known month block as the calendar month.
        # The command's row parser supplies the block month separately.
        raise ValueError(
            "Excel date cells need block-aware parsing; use parse_source_date_block."
        )

    if isinstance(value, date):
        raise ValueError(
            "Excel date cells need block-aware parsing; use parse_source_date_block."
        )

    text = clean_text(value)
    if not text:
        return None

    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            parsed = datetime.strptime(text, fmt).date()
            # Known source typo.
            if parsed == date(2028, 8, 28):
                parsed = date(2026, 8, 28)
            return parsed
        except ValueError:
            pass

    raise ValueError(f"Unrecognized expense date: {value!r}")


def parse_amount(value):
    if value is None or clean_text(value) == "":
        return None

    if isinstance(value, Decimal):
        return value

    if isinstance(value, (int, float)):
        return Decimal(str(value)).quantize(Decimal("0.01"))

    text = clean_text(value).replace(",", "")
    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ValueError(f"Invalid expense amount: {value!r}")


def category_for(description):
    key = clean_text(description).upper()
    return CATEGORY_MAP.get(key, "other")


class Command(BaseCommand):
    help = "Import Dorah Dental expenses from the supplied Excel workbook."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="EXPENSES (1).xlsx",
            help="Path to the expense workbook.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Actually create Expense records. Without this flag the command is dry-run only.",
        )

    def handle(self, *args, **options):
        path = Path(options["file"]).expanduser().resolve()
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        wb = load_workbook(path, data_only=True, read_only=True)
        ws = wb[wb.sheetnames[0]]

        current_date = None
        rows = []

        for row_number, row in enumerate(
            ws.iter_rows(min_row=2, max_col=3, values_only=True),
            start=2,
        ):
            raw_date, raw_description, raw_amount = row

            if raw_date is not None:
                if isinstance(raw_date, (datetime, date)):
                    if row_number <= 76:
                        block_month = 7
                    elif row_number <= 223:
                        block_month = 8
                    elif row_number <= 328:
                        block_month = 9
                    else:
                        raise CommandError(
                            f"Row {row_number}: unexpected Excel date cell {raw_date!r}"
                        )
                    current_date = parse_source_date_block(raw_date, block_month)
                else:
                    current_date = parse_source_date_block(raw_date)


            description = clean_text(raw_description)
            amount = parse_amount(raw_amount)

            if not description and amount is None:
                continue

            if not current_date:
                raise CommandError(
                    f"Row {row_number}: expense has no usable date before it."
                )

            if not description:
                raise CommandError(
                    f"Row {row_number}: amount {amount} has no expense description."
                )

            rows.append(
                {
                    "row": row_number,
                    "date": current_date,
                    "description": description,
                    "amount": amount,
                    "category": category_for(description),
                    "reference": f"EXP-XL-{row_number:04d}",
                }
            )

        existing_refs = set(
            Expense.objects.filter(
                reference_number__startswith="EXP-XL-"
            ).values_list("reference_number", flat=True)
        )

        new_rows = [r for r in rows if r["reference"] not in existing_refs]
        already_imported = [r for r in rows if r["reference"] in existing_refs]
        blank_amount = [r for r in new_rows if r["amount"] is None]
        importable = [r for r in new_rows if r["amount"] is not None]

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("DORAH DENTAL EXPENSE IMPORT"))
        self.stdout.write(f"Workbook: {path}")
        self.stdout.write(f"Source expense lines: {len(rows)}")
        self.stdout.write(f"Already imported: {len(already_imported)}")
        self.stdout.write(f"New expense lines: {len(new_rows)}")
        self.stdout.write(f"Importable lines: {len(importable)}")
        self.stdout.write(f"Blank-amount lines (skipped): {len(blank_amount)}")

        if blank_amount:
            self.stdout.write("")
            self.stdout.write("BLANK AMOUNT ROWS:")
            for item in blank_amount:
                self.stdout.write(
                    f"  Excel row {item['row']} | {item['date']} | {item['description']}"
                )

        totals = {}
        for item in importable:
            totals[item["date"].strftime("%Y-%m")] = (
                totals.get(item["date"].strftime("%Y-%m"), Decimal("0"))
                + item["amount"]
            )

        self.stdout.write("")
        self.stdout.write("MONTHLY TOTALS:")
        for month, total in sorted(totals.items()):
            self.stdout.write(f"  {month}: UGX {total:,.2f}")

        grand_total = sum(totals.values(), Decimal("0"))
        self.stdout.write(f"  TOTAL: UGX {grand_total:,.2f}")

        if not options["apply"]:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN ONLY — no database changes were made."
                )
            )
            self.stdout.write(
                "Review the totals above. Run again with --apply to import."
            )
            return

        created = 0
        with transaction.atomic():
            for item in importable:
                Expense.objects.create(
                    description=item["description"],
                    category=item["category"],
                    amount=item["amount"],
                    expense_date=item["date"],
                    payment_method="cash",
                    reference_number=item["reference"],
                    notes=f"Imported from EXPENSES (1).xlsx, Excel row {item['row']}.",
                )
                created += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"IMPORT COMPLETE — {created} expense records created."
            )
        )
        self.stdout.write(f"Total imported: UGX {grand_total:,.2f}")
