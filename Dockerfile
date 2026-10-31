# ==============================================================================
# DukaanSaathi — Production Backend Container
# Multi-stage / minimal footprint Python 3.11 Debian slim container
# Includes FFmpeg, PostgreSQL runtime libraries, curl healthcheck, and unprivileged user
# ==============================================================================

FROM python:3.11-slim

LABEL maintainer="DukaanSaathi Engineering Team"
LABEL description="DukaanSaathi Kirana Voice Commerce Backend API"
LABEL version="1.0.0-rc1"

# Environment settings for deterministic, unbuffered Python runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    APP_ENV=production

# Install system dependencies:
# - ffmpeg: Required for server-side audio validation & browser format transcoding
# - libpq5: Required for psycopg2 / PostgreSQL connectivity
# - curl: Required for Docker container health check probes
# - ca-certificates: Required for secure outbound HTTPS to Gnani AI endpoints
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user and group (Least Privilege Security)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# Install Python dependencies with pip wheel caching layer
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend codebase, migrations, seed data, and configuration
COPY --chown=appuser:appgroup backend/ ./backend/
COPY --chown=appuser:appgroup data/ ./data/

# Set file permissions and switch to unprivileged user
USER appuser

# Expose standard application port
EXPOSE 8000

# Container health probe via safe readiness endpoint (zero side-effects)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health/ready || exit 1

# Production ASGI server launch command:
# 1 worker enforced due to in-memory sliding window rate limiting (requires Redis for >1 workers)
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]

