"""Final safety net: never expose Django tracebacks to end users."""

import logging
from .error_handlers import server_error

logger = logging.getLogger(__name__)


class FriendlyExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except Exception:
            # server_error logs the traceback and gives the user a safe page.
            return server_error(request)
