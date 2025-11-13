# ===============================
# THE13TH — Production Dockerfile
# Day 9 (Stability Fix)
# ===============================

# ----------------------
# 1. Build Frontend
# ----------------------
FROM node:18 AS frontend
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps

COPY frontend .
RUN npm run build

# ----------------------
# 2. Backend Runtime
# ----------------------
FROM python:3.10-slim AS backend
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Backend deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Backend application
COPY app ./app
COPY config ./config
COPY data ./data
COPY static ./static
COPY templates ./templates

# Copy full frontend source (optional but safe)
COPY frontend ./frontend

# Copy compiled SPA build
COPY --from=frontend /app/frontend/dist ./frontend/dist

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
