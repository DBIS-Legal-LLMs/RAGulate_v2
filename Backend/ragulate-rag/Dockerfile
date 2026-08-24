# ──────────────────────────────────────────────────────────────
# Stage 1 – build / install deps
# ──────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps needed by Python packages:
#   build-essential  — compiles C extensions (e.g. tiktoken, tokenizers)
#   git              — some pip packages fetch git metadata at install time
#   libgl1 / libglib — required by PyMuPDF / LightRAG
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ──────────────────────────────────────────────────────────────
# Stage 2 – runtime image
# ──────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# System runtime libs (no build-essential needed here)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY app/ ./app/
COPY scripts/ ./scripts/

# Expose the port uvicorn will listen on
EXPOSE 8081

# Run FastAPI via uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8081"]
