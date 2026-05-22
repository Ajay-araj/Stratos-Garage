"""
Health-check endpoint — GET /api/health/

Returns HTTP 200 if the application and database are reachable, 503 otherwise.
Used by load balancers, Docker health checks, and monitoring systems.
"""
import time
import logging

from django.db import connection, OperationalError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # Skip JWT — health check must not require auth

    def get(self, request):
        checks = {}
        overall_ok = True

        # ── Database ──────────────────────────────────────────────────────────
        t0 = time.monotonic()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            checks['database'] = {
                'status': 'ok',
                'latency_ms': round((time.monotonic() - t0) * 1000, 2),
            }
        except OperationalError as exc:
            checks['database'] = {'status': 'error', 'detail': str(exc)}
            overall_ok = False
            logger.error(f"Health check — DB unreachable: {exc}")

        http_status = status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(
            {
                'status': 'ok' if overall_ok else 'degraded',
                'checks': checks,
            },
            status=http_status,
        )
