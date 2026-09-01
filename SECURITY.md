# Dora's Dental Gem — Security Notes

## Production environment variables
Never commit `SECRET_KEY`, `DATABASE_URL`, SMS API keys, or other credentials. Set them in Railway/environment secrets.

## Authentication
- Staff login uses password + OTP for the current browser session.
- OTP codes are stored as SHA-256 hashes and expire after 5 minutes.
- OTP resend has a 60-second cooldown.
- django-axes limits repeated password failures.
- Session cookies are secure/HTTP-only in production.
- Sensitive web pages require successful OTP verification.

## API
- Public endpoints are limited to service/doctor discovery and booking requests.
- Patient, billing, inventory, reporting, settings, and staff endpoints require authentication.
- API login no longer disables CSRF globally.

## Deployment
Set `DEBUG=False`, a strong `SECRET_KEY`, a restricted `ALLOWED_HOSTS`, HTTPS, and a valid `DATABASE_URL` before production deployment.
