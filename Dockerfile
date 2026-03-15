FROM python:3.11-slim

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
