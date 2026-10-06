from django.core.management.base import BaseCommand
from django.conf import settings
from django.urls import get_resolver


class Command(BaseCommand):
    help = 'Run basic production security checks for Dorah Dental.'

    def handle(self, *args, **options):
        failures = []
        checks = []

        if settings.DEBUG:
            failures.append('DEBUG is enabled.')
        checks.append(('DEBUG=False', not settings.DEBUG))

        if not settings.SECRET_KEY or settings.SECRET_KEY.startswith('dev-only-'):
            failures.append('SECRET_KEY is missing or using the development fallback.')
        checks.append(('Strong SECRET_KEY configured', bool(settings.SECRET_KEY) and not settings.SECRET_KEY.startswith('dev-only-')))

        checks.append(('HTTPS redirect enabled in production', bool(getattr(settings, 'SECURE_SSL_REDIRECT', False)) if not settings.DEBUG else True))
        checks.append(('Secure session cookie', bool(getattr(settings, 'SESSION_COOKIE_SECURE', False)) if not settings.DEBUG else True))
        checks.append(('Secure CSRF cookie', bool(getattr(settings, 'CSRF_COOKIE_SECURE', False)) if not settings.DEBUG else True))
        checks.append(('HSTS enabled in production', bool(getattr(settings, 'SECURE_HSTS_SECONDS', 0)) if not settings.DEBUG else True))

        routes = []
        def walk(patterns, prefix=''):
            for pattern in patterns:
                route = prefix + str(getattr(pattern, 'pattern', ''))
                if hasattr(pattern, 'url_patterns'):
                    walk(pattern.url_patterns, route)
                elif route:
                    routes.append(route)
        walk(get_resolver().url_patterns)
        debug_routes = [r for r in routes if 'debug/app' in r]
        checks.append(('Public debug endpoint removed', not debug_routes))
        if debug_routes:
            failures.append('Public debug endpoint still registered: ' + ', '.join(debug_routes))

        for label, ok in checks:
            self.stdout.write(('PASS: ' if ok else 'FAIL: ') + label)

        if failures:
            self.stderr.write(self.style.ERROR('Security audit failed:'))
            for item in failures:
                self.stderr.write(' - ' + item)
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS('Security audit passed.'))
