# Backend/Dockerfile

FROM python:3.11-slim

# System Dependencies
RUN apt update && apt install -y build-essential && rm -rf /var/lib/apt/lists/*

# Arbeitsverzeichnis im Container
WORKDIR /app

# Requirements in den Container kopieren
COPY requirements.txt /app/requirements.txt

# Requirements installieren
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

# Backend-Code in den Container kopieren
COPY . /app/Backend

# Arbeitsverzeichnis im Container auf Backend setzen
WORKDIR /app/Backend

# Version set by CI (e.g. 1.2.3), returned by GET /api/health
ARG APP_VERSION=local
ENV APP_VERSION=$APP_VERSION

# Uvicorn starten (FastAPI app)
CMD ["uvicorn", "api_v2.app.main:app", "--host", "0.0.0.0", "--port", "8000"]