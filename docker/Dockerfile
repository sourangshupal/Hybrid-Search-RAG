# Multi-stage Dockerfile for Hybrid Search RAG API
# Optimized for production with minimal image size

# Stage 1: Builder
# Install dependencies and prepare virtual environment
FROM python:3.12-slim as builder

# Set build arguments
ARG UV_VERSION=0.1.18

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install --no-cache-dir uv==${UV_VERSION}

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./
COPY README.md ./

# Create virtual environment and install dependencies
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache -e .

# Stage 2: Runtime
# Minimal runtime image
FROM python:3.12-slim

# Set build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

# Labels for metadata
LABEL maintainer="your-email@example.com" \
      org.label-schema.build-date="${BUILD_DATE}" \
      org.label-schema.vcs-ref="${VCS_REF}" \
      org.label-schema.version="${VERSION}" \
      org.label-schema.name="Hybrid Search RAG API" \
      org.label-schema.description="Production-ready RAG system for academic research" \
      org.label-schema.schema-version="1.0"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && \
    useradd -r -g appuser -u 1000 -s /bin/bash -m appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser scripts ./scripts
COPY --chown=appuser:appuser configs ./configs

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/models && \
    chown -R appuser:appuser /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    LOG_LEVEL=INFO \
    ENVIRONMENT=production

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
