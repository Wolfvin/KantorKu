# ── Stage 1: Base ──
FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency specification first for caching
COPY framework/pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir ".[all]"

# ── Stage 2: Application ──
FROM base AS app

# Copy application code
COPY framework/kantorku/ kantorku/
COPY framework/workers/ workers/
COPY framework/kantorku.toml .

# Create data directory
RUN mkdir -p /app/data

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the server
CMD ["kantorku", "serve", "--host", "0.0.0.0", "--port", "8000"]
