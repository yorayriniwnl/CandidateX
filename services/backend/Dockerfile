# ==============================================================================
# Candidate Capability Intelligence (CCI) - Backend Dockerfile
# Multi-stage, non-root, security-hardened container for FastAPI Core
# Invariant: Candidate code is NEVER executed in this container.
# ==============================================================================

# Stage 1: Build virtual environment & dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --upgrade pip setuptools wheel && \
    pip install .

# Stage 2: Minimal, non-root runtime environment
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_ENV=production \
    PORT=8000

# Create unprivileged system group and user
RUN groupadd -g 10001 cci && \
    useradd -u 10001 -g cci -s /usr/sbin/nologin -d /app -M cci

# Copy virtualenv and application code
COPY --from=builder /opt/venv /opt/venv
COPY src/ /app/src/
COPY pyproject.toml /app/pyproject.toml

# Create scratch directory with permissions for non-root candidate isolation
RUN mkdir -p /app/tmp && chown -R cci:cci /app

USER cci

EXPOSE 8000

# Health check without external curl dependency
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; sys_exit = 0 if urllib.request.urlopen('http://localhost:8000/healthz').getcode() == 200 else 1; exit(sys_exit)"

CMD ["uvicorn", "cci.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
