# ----------------------
# 1. Build Frontend
# ----------------------
FROM node:18 AS frontend

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend .
RUN npm run build

# ----------------------
# 2. Build Backend
# ----------------------
FROM python:3.10-slim AS backend

WORKDIR /app

# Install backend deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ❗ ONLY COPY THE13TH BACKEND CODE — not entire repo
COPY app ./app
COPY config ./config
COPY data ./data
COPY static ./static
COPY templates ./templates
COPY frontend ./frontend/      # so SPA dist exists at runtime

# Bring in the built frontend output
COPY --from=frontend /app/frontend/dist ./frontend/dist

ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
