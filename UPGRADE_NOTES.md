# Dora's Dental Gem — Security & UX Upgrade

## Included
- Hardened production Django settings (DEBUG/hosts/CSRF/CORS/HTTPS/session security).
- Removed hard-coded PostgreSQL and Yoola credentials; use environment variables.
- Added django-axes brute-force protection.
- Added session-bound OTP enforcement across authenticated web pages.
- OTPs are hashed at rest, expire after 5 minutes, and have a 60-second resend cooldown.
- Removed the debug/master OTP bypass.
- API login no longer disables CSRF globally; sensitive API resources require authenticated clinic staff.
- Added DRF request throttling.
- Added appointment indexes and an active doctor-slot uniqueness constraint.
- Added optional `Patient.user` linkage for authenticated patient/API workflows.
- Patient portal PINs are hashed; migration upgrades existing plaintext PINs.
- Added responsive mobile navigation and improved form/card/table styling.
- Added installable PWA manifest, icons, service worker and offline fallback.
- Added a password visibility control to staff login.
- Logout is now POST + CSRF protected.

## Before production deployment
1. Set a strong `SECRET_KEY`.
2. Set `DEBUG=False`.
3. Set the exact `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
4. Set `DATABASE_URL` to the new/rotated database credential.
5. Set `YOOLA_API_KEY` as a Railway secret if SMS is required.
6. Rotate the database password and Yoola API key that were previously embedded in the old project settings.
7. Run `python manage.py migrate` and `python manage.py collectstatic --noinput`.
8. Run `python manage.py check --deploy`.

## Important compatibility note
The web app now requires OTP verification for authenticated browser sessions. API endpoints use token authentication and are excluded from the browser OTP middleware.
