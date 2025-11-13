# ============================================================
# THE13TH — Stable Production Dockerfile (Day 9 Fix)
# ============================================================
# Frontend build stage
FROM node:18 AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps
COPY frontend .
RUN npm run build

# Backend stage
FROM python:3.10-slim AS backend
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy backend app code
COPY app ./app
COPY config ./config
COPY data ./data
COPY static ./static
COPY templates ./templates

# Copy built SPA
COPY --from=frontend /app/frontend/dist /app/frontend/dist

ENV PORT=8000
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
