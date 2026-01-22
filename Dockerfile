# syntax=docker/dockerfile:1

# --- Stage 1: Build Python deps into a venv (keeps final image smaller/cleaner) ---
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install --no-cache-dir -r /app/requirements.txt


# --- Stage 2: Runtime with Playwright browsers preinstalled ---
# This image includes Chromium + all OS deps for Playwright.
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
