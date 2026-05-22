#!/bin/sh
# entrypoint.sh — runs before gunicorn starts
set -e

echo "[entrypoint] Running migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "[entrypoint] Starting server..."
exec "$@"
