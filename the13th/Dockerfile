# ----------------------
# 1. Build Frontend
# ----------------------
FROM node:18 AS frontend

WORKDIR /app

# Copy frontend from correct location inside build context
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm install

COPY frontend ./frontend
RUN cd frontend && npm run build

# ----------------------
# 2. Build Backend
# ----------------------
FROM python:3.10-slim AS backend

WORKDIR /app

# Install backend deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy backend source
COPY . .

# ✅ Copy built frontend into exact location FastAPI expects
COPY --from=frontend /app/frontend/dist /app/frontend/dist

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
