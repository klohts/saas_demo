# --- Build stage: build React with Node 20 ---
FROM node:20-bullseye as builder
WORKDIR /app

# copy only what we need to leverage caching
COPY frontend/package.json frontend/package-lock.json* ./frontend/
COPY frontend/ ./frontend/
WORKDIR /app/frontend

RUN npm ci --no-audit --no-fund
RUN npm run build

# --- Runtime stage: Python + FastAPI ---
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1

# create app user
RUN useradd --create-home appuser
WORKDIR /app

# install runtime deps
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

# copy backend + static assets from builder
COPY . /app
# copy built frontend
COPY --from=builder /app/frontend/dist /app/static

# ensure static is readable
RUN chown -R appuser:appuser /app
USER appuser

ENV APP_PORT=8012
EXPOSE 8012

CMD ["uvicorn", "setup_frontend_serving:app", "--host", "0.0.0.0", "--port", "8012"]
