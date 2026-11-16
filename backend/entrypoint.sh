#!/bin/sh
# entrypoint.sh — runs before gunicorn starts
set -eu

if [ "${1:-}" = "gunicorn" ]; then
    echo "[entrypoint] Running migrations..."
    if ! python manage.py migrate --noinput; then
        echo "[entrypoint] Database migrations failed; refusing to start." >&2
        exit 1
    fi

    echo "[entrypoint] Collecting static files..."
    if ! python manage.py collectstatic --noinput --clear; then
        echo "[entrypoint] Static file collection failed; refusing to start." >&2
        exit 1
    fi

    echo "[entrypoint] Starting server..."
else
    echo "[entrypoint] Starting non-web command..."
fi

exec "$@"
