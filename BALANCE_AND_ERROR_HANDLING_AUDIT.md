# Dorah Dental — Stabilization Notes

## Financial balance fix
- Register-imported invoices (`REG-*` / notes containing `Imported from corrected register:`) contain cumulative balance snapshots.
- The latest register balance is therefore used once per patient instead of summing historical snapshots.
- Normal invoices remain independent and their outstanding balances are summed.
- Patient list/search and patient portal now use the canonical balance calculation.
- Existing invoice records are not deleted or rewritten by this fix.

## OTP and error handling
- Expired/failed/used OTPs clear `otp_code` with an empty string, matching the non-null database field.
- Unexpected server exceptions receive a safe error page with a reference code while technical details remain in server logs.
- Common caught web exceptions no longer expose raw Python/Django exception text to users.
- API error responses use a generic message instead of returning exception text.

## Validation
- Modified Python files pass `py_compile` syntax validation.
- Full Django `manage.py check` / database tests must be run in the project's normal environment where Django and its configured database are installed.
