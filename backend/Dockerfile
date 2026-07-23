# =============================================================================
# Abhinav Group — AI Gmail Intelligence Assistant
# Backend Dockerfile — Multi-stage Build
# =============================================================================

# --- Base Stage (Common Dependencies) ---
FROM python:3.11-slim AS base
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# --- Builder Stage (Install Python Packages) ---
FROM base AS builder
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Development Stage (For Local Dev) ---
FROM base AS development
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# --- Production Stage (For Deployment) ---
FROM base AS production
RUN useradd -m -s /bin/bash appuser
USER appuser
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH
COPY --chown=appuser:appuser . .
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
