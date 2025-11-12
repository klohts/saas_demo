# ----------------------
# 1. Build Frontend
# ----------------------
FROM node:18 AS frontend

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend ./
RUN npm run build

# ----------------------
# 2. Build Backend
# ----------------------
FROM python:3.10-slim AS backend

WORKDIR /app

# Copy backend dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy backend source
COPY . .

# Copy built frontend into FastAPI static dir
COPY --from=frontend /app/frontend/dist /app/frontend/dist

# Expose Render port
ENV PORT=8000
EXPOSE 8000

# Start FastAPI
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
