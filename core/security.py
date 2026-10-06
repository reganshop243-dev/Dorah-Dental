from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def permission_required(permission_code, *, ajax_status=403):
    """Enforce a clinic permission on a Django view.

    This complements the UI and prevents authenticated low-privilege users
    from reaching protected actions by typing the URL directly.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            profile = getattr(user, 'profile', None)
            if profile is None or not profile.is_active or not profile.has_permission(permission_code):
                if request.headers.get('Accept', '').startswith('application/json') or request.path.startswith('/api/'):
                    from django.http import JsonResponse
                    return JsonResponse({'detail': 'You do not have permission to perform this action.'}, status=ajax_status)
                messages.error(request, 'Access denied. You do not have permission to perform this action.')
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator
