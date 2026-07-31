# Backend API image for the Parts monorepo.
#
# Build from monorepo root (required so src/parrts is available):
#   docker build -f backend/Dockerfile -t parts-backend .
#
# docker-compose.prod.yml sets context: . and dockerfile: backend/Dockerfile.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/src \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Dependencies first for better layer caching
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Application code (backend as /app) + modern parrts core (read-only at /src)
COPY backend/ /app/
COPY src/ /src/

RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app /src
USER appuser

EXPOSE 8000

# Production default: no --reload (compose.prod overrides workers as needed)
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
