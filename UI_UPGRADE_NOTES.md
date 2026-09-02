# Dora's Dental Gem — UI Upgrade

## Completed in this upgrade
- Replaced the conflicting mobile sidebar CSS with one phone-first responsive system.
- Mobile navigation now opens as a full labelled sidebar with backdrop, Escape-to-close, link-to-close and resize handling.
- Removed the old 70px icon-only mobile sidebar behavior.
- Added a reusable `static/css/app.css` design system for cards, statistics, forms, tables, buttons, alerts and dashboard actions.
- Rebuilt the general, admin, doctor, receptionist and accountant dashboards using the existing backend context/data.
- Added responsive dashboard quick actions and mobile-friendly stat grids.
- Added `static/css/portal.css` and improved the patient portal dashboard for phones.
- Fixed the invalid PWA manifest JSON apostrophe escaping.
- Updated the service-worker cache to include the new application stylesheet and bumped the cache version.
- Added the missing `templates/inventory/delete.html` required by `inventory_delete`.
- Cleaned dashboard navigation URLs in the base template so generated hrefs contain no formatting whitespace.

## Validation performed
- All 153 Python source files compile successfully with `py_compile`.
- PWA manifest parses as valid JSON.
- Changed Django templates have balanced `if/endif` and `block/endblock` tags.
- Static scan found no remaining 70px mobile-sidebar rules.
- Static scan of `render()` calls found no missing template except the inventory delete template, which was added.
- Django runtime `manage.py check` could not be executed in the audit environment because Django is not installed in that environment. Run it in the project's virtual environment before deployment.

## Recommended local verification
```powershell
$env:DEBUG="True"
$env:SECRET_KEY="local-dorah-dental-dev-key-2026"
python manage.py check
python manage.py collectstatic --noinput
python manage.py runserver
```

Then test at desktop and phone widths, especially:
- `/` dashboard
- `/patients/`
- `/appointments/appointments/`
- `/billing/`
- `/inventory/`
- `/portal/`
