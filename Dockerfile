FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN apt-get update && apt-get install -y curl nodejs npm build-essential --no-install-recommends || true
RUN pip install --no-cache-dir fastapi uvicorn python-dotenv
WORKDIR /app/frontend
RUN npm install --legacy-peer-deps || true
RUN npm run build || true
WORKDIR /app
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]

