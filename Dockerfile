# Pinned to an exact patch so the runtime is reproducible and so runtime.txt
# can state something true. `3.11-slim` floats across patch releases, which
# means a declared version can never be more than approximately right.
#
# This file is the authoritative runtime: Railway builds with the Dockerfile
# when one is present at the repo root, so the CMD below -- not the Procfile --
# is what actually starts the app.
#
# Bump deliberately: an exact pin also freezes base-image security updates.
FROM python:3.11.17-slim

RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/healthz || exit 1

CMD gunicorn \
    --workers=2 \
    --threads=2 \
    --timeout=120 \
    --keep-alive=5 \
    --max-requests=1000 \
    --max-requests-jitter=100 \
    --preload \
    --bind=0.0.0.0:${PORT:-8080} \
    --access-logfile=- \
    --error-logfile=- \
    --log-level=info \
    wsgi:app
