# ============================================================================
# Multi-stage Dockerfile for Law Agent Docker Deployment
# ============================================================================
# Stage 1: Builder
# Installs dependencies using uv for fast package installation
FROM python:3.13-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    postgresql-client \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files and source for installation
COPY pyproject.toml README.md ./
COPY src ./src

# Create virtual environment and install package with all dependencies
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache-dir .

# ============================================================================
# Stage 2: Runtime
# Minimal image with only runtime dependencies
FROM python:3.13-slim

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Copy virtual environment from builder
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

# Copy application code and configuration
COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser .chainlit ./.chainlit
COPY --chown=appuser:appuser public ./public
COPY --chown=appuser:appuser config.yaml .
COPY --chown=appuser:appuser chainlit.md .

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=30s \
    CMD curl -f http://localhost:8000/health || exit 1

# Run Chainlit application
CMD ["chainlit", "run", "src/law_assistant/ui/app.py", "--host", "0.0.0.0", "--port", "8000"]
