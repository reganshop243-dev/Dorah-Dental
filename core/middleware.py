from django.shortcuts import redirect
from django.urls import reverse


class OTPVerificationMiddleware:
    """Require OTP verification for authenticated web sessions.

    API clients use token authentication and are intentionally excluded.
    """
    EXEMPT_PREFIXES = (
        '/login/', '/logout/', '/otp-verify/', '/otp-send/',
        '/static/', '/media/', '/api/', '/portal/', '/sw.js', '/offline/'
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.path.startswith(self.EXEMPT_PREFIXES):
            if not request.session.get('otp_verified') or request.session.get('otp_user_id') != request.user.pk:
                return redirect(f"{reverse('core:otp_verify')}?next={request.get_full_path()}")
        return self.get_response(request)
