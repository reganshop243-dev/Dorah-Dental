# Dorah Dental — Register Rebuild

This project includes a rebuilt import workbook generated from the complete `REGISTER (5)(1).xlsx` register.

## What changed

The old importer treated every row's `BALANCE` as a new debt. That is incorrect because the register balance is a **running patient balance**.

The rebuilt ledger calculates:

`incremental charge = current balance + amount paid - previous patient balance`

Payments are then allocated across the patient's open register invoices in date order. Negative implied charges are treated as register write-offs/adjustments, not as fake payments.

## Source data

- 2,437 transaction rows
- 1,345 patient ledger groups
- Register period: 05/06/2026 through 28/09/2026
- Every patient summary reconciles: total implied charges = total payments + final balance

## Import

The command is still named `import_register_dmy_v10` so existing deployment commands do not need to change.

### 1. Dry run first

```powershell
python manage.py import_register_dmy_v10 "Dorah_Dental_Register_REBUILT_LEDGER.xlsx" --dry-run
```

### 2. Reset and rebuild

**This intentionally clears the existing patients, appointments, treatments, invoices, invoice items and payments before rebuilding them from the workbook. Users are preserved.**

```powershell
python manage.py import_register_dmy_v10 "Dorah_Dental_Register_REBUILT_LEDGER.xlsx" --reset
```

### 3. Verify balances

```powershell
python manage.py verify_register_ledger "Dorah_Dental_Register_REBUILT_LEDGER.xlsx"
```

The final verification should report:

```text
Mismatches: 0
REGISTER LEDGER VERIFIED: all patient balances match the workbook.
```

Do not run the old importer after this rebuild, because it will reintroduce the running-balance double-counting problem.
