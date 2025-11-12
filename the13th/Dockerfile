# ============================================
# THE13TH — Render Staging Dockerfile
# ============================================

# ---------- Stage 1: Build Frontend ----------
FROM node:18-alpine AS builder
WORKDIR /app/frontend
ENV NODE_ENV=production
COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps --silent
COPY frontend .
RUN npm run build

# ---------- Stage 2: Build Backend ----------
FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev ca-certificates curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=builder /app/frontend/dist /app/static

RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://127.0.0.1:8000/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
