# ---- Stage: build and runtime combined (simplified) ----
FROM python:3.12-slim

# Set up app working directory
WORKDIR /app

# Install system dependencies (Node, npm, build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl nodejs npm build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker cache
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy entire project
COPY . .

# Build frontend
WORKDIR /app/frontend
RUN npm install --legacy-peer-deps
RUN npm run build

# Return to app root
WORKDIR /app

# Ensure Python can resolve backend package
ENV PYTHONPATH=/app

# Expose FastAPI port
EXPOSE 8000

# Default start command
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
