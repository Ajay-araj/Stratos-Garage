
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# System dependencies needed to compile Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# Runtime image
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=Stratosgarage.settings \
    DJANGO_ENV=production \
    HOME=/tmp \
    TMPDIR=/tmp

WORKDIR /app

# Runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links /wheels -r requirements.txt \
    && rm -rf /wheels

# Copy application source
COPY . .

# Create application directories
RUN mkdir -p /app/media /app/staticfiles /app/logs

# Copy and prepare entrypoint BEFORE switching users
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create non-root user and assign permissions
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup --home /tmp --no-create-home appuser \
    && chown -R appuser:appgroup /app \
    && chown root:root /entrypoint.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import os, urllib.request; port = os.environ.get('PORT', '8000'); host = (os.environ.get('ALLOWED_HOSTS') or 'api.stratosgarage.com').split(',')[0].strip(); request = urllib.request.Request('http://127.0.0.1:' + port + '/api/health/', headers={'Host': host, 'X-Forwarded-Proto': 'https'}); urllib.request.urlopen(request, timeout=5)" || exit 1

ENTRYPOINT ["/entrypoint.sh"]

CMD ["gunicorn", "Stratosgarage.wsgi:application", "--config", "gunicorn.conf.py"]
