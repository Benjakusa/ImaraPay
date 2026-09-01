FROM python:3.12-slim AS base

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

# Expose Django dev/gunicorn port
EXPOSE 8000

# Entrypoint: migrate then start server
COPY --chown=appuser:appgroup docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
