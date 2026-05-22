"""
Custom exception handler — all API errors return a consistent JSON envelope:

    {
        "error": "Human-readable summary",
        "detail": <original DRF detail — string | dict | list>,
        "code": "error_code_string"
    }
"""

import logging

from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def _flatten_errors(detail) -> str:
    """Recursively extract the first human-readable message from DRF error detail."""
    if isinstance(detail, list):
        return _flatten_errors(detail[0]) if detail else "An error occurred."
    if isinstance(detail, dict):
        first_key = next(iter(detail))
        return f"{first_key}: {_flatten_errors(detail[first_key])}"
    return str(detail)


def custom_exception_handler(exc, context):
    """
    Drop-in replacement for DRF's default exception handler.
    Configure in settings.py:
        REST_FRAMEWORK = { 'EXCEPTION_HANDLER': 'Stratosgarage.exceptions.custom_exception_handler' }
    """
    # Let DRF convert Django exceptions first
    if isinstance(exc, Http404):
        exc = APIException(detail="Not found.")
        exc.status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, PermissionDenied):
        exc = APIException(detail="Permission denied.")
        exc.status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, DjangoValidationError):
        exc = APIException(detail=exc.message_dict if hasattr(exc, 'message_dict') else str(exc))
        exc.status_code = status.HTTP_400_BAD_REQUEST

    response = drf_exception_handler(exc, context)

    if response is not None:
        detail = response.data

        # Normalise DRF's {"detail": "..."} wrapper
        if isinstance(detail, dict) and 'detail' in detail and len(detail) == 1:
            detail = detail['detail']

        error_summary = _flatten_errors(detail)
        code = getattr(getattr(exc, 'detail', None), 'code', None) or 'error'

        response.data = {
            'success': False,
            'message': error_summary,
            'errors': detail if isinstance(detail, dict) else {'non_field_errors': [detail]},
        }

        # Log 5xx as errors, 4xx as warnings (skip 401/404 noise)
        if response.status_code >= 500:
            logger.error(
                f"5xx [{response.status_code}] {context.get('view', '')} — {error_summary}",
                exc_info=exc,
            )
        elif response.status_code not in (401, 404):
            logger.warning(
                f"4xx [{response.status_code}] {context.get('view', '')} — {error_summary}"
            )

    return response
