"""Safe, user-facing error handlers for Dorah Dental."""

import logging
import secrets

from django.http import HttpResponse
from django.shortcuts import render

logger = logging.getLogger(__name__)


def _error_reference():
    return f"DD-{secrets.token_hex(4).upper()}"


def _render_error(request, status, title, message):
    reference = _error_reference()
    return render(
        request,
        "errors/error.html",
        {
            "status_code": status,
            "error_title": title,
            "error_message": message,
            "error_reference": reference,
        },
        status=status,
    )


def bad_request(request, exception=None):
    return _render_error(
        request, 400, "Request could not be completed",
        "The information sent to Dorah Dental was not valid. Please try again.",
    )


def permission_denied(request, exception=None):
    return _render_error(
        request, 403, "Access not available",
        "You do not have permission to access this page.",
    )


def page_not_found(request, exception=None):
    return _render_error(
        request, 404, "Page not found",
        "The page you requested could not be found. It may have moved or the address may be incorrect.",
    )


def server_error(request):
    reference = _error_reference()
    logger.error(
        "Unhandled Dorah Dental server error reference=%s path=%s",
        reference,
        getattr(request, "path", ""),
        exc_info=True,
    )
    return render(
        request,
        "errors/error.html",
        {
            "status_code": 500,
            "error_title": "Something went wrong",
            "error_message": "We could not complete your request right now. Please try again. If the problem continues, contact the administrator.",
            "error_reference": reference,
        },
        status=500,
    )
