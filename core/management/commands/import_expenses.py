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


def parse_source_date(value, block_month=None):
    """
    Parse expense dates.

    The workbook contains two types of dates:

    1. Normal text dates:
       DD/MM/YYYY

    2. Real Excel date cells from the beginning of the workbook.
       Those cells were entered in a way that Excel interpreted
       incorrectly.

       Example:
           Excel date 2026-01-07
           Intended date 07/07/2026

           Excel date 2026-02-07
           Intended date 07/08/2026

           Excel date 2026-03-07
           Intended date 07/09/2026

       For these cells, the Excel MONTH represents the intended
       day, while block_month represents the intended calendar month.
    """

    if isinstance(value, datetime):
        if block_month is None:
            raise ValueError(
                f"Excel date cell requires a block month: {value!r}"
            )

        intended_day = value.month

        try:
            return date(2026, block_month, intended_day)
        except ValueError as exc:
            raise ValueError(
                f"Invalid block date: {value!r}, "
                f"block month={block_month}"
            ) from exc

    if isinstance(value, date):
        if block_month is None:
            raise ValueError(
                f"Excel date cell requires a block month: {value!r}"
            )

        intended_day = value.month

        try:
            return date(2026, block_month, intended_day)
        except ValueError as exc:
            raise ValueError(
                f"Invalid block date: {value!r}, "
                f"block month={block_month}"
            ) from exc

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
        return value.quantize(Decimal("0.01"))

    if isinstance(value, (int, float)):
        return Decimal(str(value)).quantize(Decimal("0.01"))

    text = clean_text(value).replace(",", "")

    try:
        return Decimal(text).quantize(Decimal("0.01"))

    except InvalidOperation as exc:
        raise ValueError(
            f"Invalid expense amount: {value!r}"
        ) from exc


def category_for(description):
    key = clean_text(description).upper()

    return CATEGORY_MAP.get(key, "other")


class Command(BaseCommand):

    help = (
        "Import Dorah Dental expenses from the supplied Excel workbook."
    )

    def add_arguments(self, parser):

        parser.add_argument(
            "--file",
            default="EXPENSES (1).xlsx",
            help="Path to the expense workbook.",
        )

        parser.add_argument(
            "--apply",
            action="store_true",
            help=(
                "Actually create Expense records. "
                "Without this flag the command is dry-run only."
            ),
        )

    def handle(self, *args, **options):

        path = Path(options["file"]).expanduser().resolve()

        if not path.exists():
            raise CommandError(
                f"File not found: {path}"
            )

        self.stdout.write("=" * 60)
        self.stdout.write("DORAH DENTAL EXPENSE IMPORT")
        self.stdout.write("=" * 60)

        self.stdout.write(
            f"Workbook: {path}"
        )

        self.stdout.write(
            f"Database engine: "
            f"{transaction.get_connection().settings_dict.get('ENGINE')}"
        )

        self.stdout.write("=" * 60)

        wb = load_workbook(
            path,
            data_only=True,
            read_only=True,
        )

        if not wb.sheetnames:
            raise CommandError(
                "The workbook contains no sheets."
            )

        ws = wb[wb.sheetnames[0]]

        current_date = None
        rows = []

        for row_number, row in enumerate(
            ws.iter_rows(
                min_row=2,
                max_col=3,
                values_only=True,
            ),
            start=2,
        ):

            raw_date, raw_description, raw_amount = row

            # ---------------------------------------------------------
            # DATE
            # ---------------------------------------------------------

            if raw_date is not None:

                if isinstance(raw_date, (datetime, date)):

                    # The first malformed date blocks belong to:
                    #
                    # July      -> rows 2-76
                    # August    -> rows 77-223
                    # September -> rows 224-328
                    #
                    # For those Excel date cells, the Excel month
                    # represents the intended day.

                    if row_number <= 76:
                        block_month = 7

                    elif row_number <= 223:
                        block_month = 8

                    elif row_number <= 328:
                        block_month = 9

                    else:
                        raise CommandError(
                            f"Row {row_number}: "
                            f"unexpected Excel date cell "
                            f"{raw_date!r}"
                        )

                    try:
                        current_date = parse_source_date(
                            raw_date,
                            block_month,
                        )

                    except ValueError as exc:
                        raise CommandError(
                            f"Row {row_number}: {exc}"
                        ) from exc

                else:

                    try:
                        current_date = parse_source_date(
                            raw_date
                        )

                    except ValueError as exc:
                        raise CommandError(
                            f"Row {row_number}: {exc}"
                        ) from exc

            # ---------------------------------------------------------
            # DESCRIPTION / AMOUNT
            # ---------------------------------------------------------

            description = clean_text(
                raw_description
            )

            amount = parse_amount(
                raw_amount
            )

            # Completely empty row.
            if not description and amount is None:
                continue

            # Expense without a date.
            if not current_date:
                raise CommandError(
                    f"Row {row_number}: "
                    f"expense has no usable date before it."
                )

            # Amount without description.
            if not description:
                raise CommandError(
                    f"Row {row_number}: "
                    f"amount {amount} has no expense description."
                )

            rows.append(
                {
                    "row": row_number,
                    "date": current_date,
                    "description": description,
                    "amount": amount,
                    "category": category_for(
                        description
                    ),
                    "reference": (
                        f"EXP-XL-{row_number:04d}"
                    ),
                }
            )

        # -------------------------------------------------------------
        # DUPLICATE PROTECTION
        # -------------------------------------------------------------

        existing_refs = set(
            Expense.objects.filter(
                reference_number__startswith="EXP-XL-"
            ).values_list(
                "reference_number",
                flat=True,
            )
        )

        new_rows = [
            r
            for r in rows
            if r["reference"] not in existing_refs
        ]

        already_imported = [
            r
            for r in rows
            if r["reference"] in existing_refs
        ]

        blank_amount = [
            r
            for r in new_rows
            if r["amount"] is None
        ]

        importable = [
            r
            for r in new_rows
            if r["amount"] is not None
        ]

        # -------------------------------------------------------------
        # SUMMARY
        # -------------------------------------------------------------

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "EXPENSE WORKBOOK ANALYSIS"
            )
        )

        self.stdout.write(
            f"Source expense lines: {len(rows)}"
        )

        self.stdout.write(
            f"Already imported: {len(already_imported)}"
        )

        self.stdout.write(
            f"New expense lines: {len(new_rows)}"
        )

        self.stdout.write(
            f"Importable lines: {len(importable)}"
        )

        self.stdout.write(
            f"Blank-amount lines (skipped): "
            f"{len(blank_amount)}"
        )

        # -------------------------------------------------------------
        # BLANK AMOUNTS
        # -------------------------------------------------------------

        if blank_amount:

            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "BLANK AMOUNT ROWS:"
                )
            )

            for item in blank_amount:

                self.stdout.write(
                    f"  Excel row {item['row']} | "
                    f"{item['date']} | "
                    f"{item['description']}"
                )

        # -------------------------------------------------------------
        # MONTHLY TOTALS
        # -------------------------------------------------------------

        totals = {}

        for item in importable:

            month_key = item["date"].strftime(
                "%Y-%m"
            )

            totals[month_key] = (
                totals.get(
                    month_key,
                    Decimal("0"),
                )
                + item["amount"]
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "MONTHLY TOTALS:"
            )
        )

        for month, total in sorted(
            totals.items()
        ):

            self.stdout.write(
                f"  {month}: "
                f"UGX {total:,.2f}"
            )

        grand_total = sum(
            totals.values(),
            Decimal("0"),
        )

        self.stdout.write(
            f"  TOTAL: UGX {grand_total:,.2f}"
        )

        # -------------------------------------------------------------
        # DRY RUN
        # -------------------------------------------------------------

        if not options["apply"]:

            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN ONLY — "
                    "NO DATABASE CHANGES WERE MADE."
                )
            )

            self.stdout.write("")
            self.stdout.write(
                "Run with --apply only after "
                "reviewing the totals."
            )

            return

        # -------------------------------------------------------------
        # ACTUAL IMPORT
        # -------------------------------------------------------------

        created = 0

        with transaction.atomic():

            for item in importable:

                Expense.objects.create(
                    description=item[
                        "description"
                    ],

                    category=item[
                        "category"
                    ],

                    amount=item[
                        "amount"
                    ],

                    expense_date=item[
                        "date"
                    ],

                    payment_method="cash",

                    reference_number=item[
                        "reference"
                    ],

                    notes=(
                        "Imported from "
                        "EXPENSES_IMPORT_READY.xlsx, "
                        f"Excel row {item['row']}."
                    ),
                )

                created += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"IMPORT COMPLETE — "
                f"{created} expense records created."
            )
        )

        self.stdout.write(
            f"Total imported: "
            f"UGX {grand_total:,.2f}"
        )