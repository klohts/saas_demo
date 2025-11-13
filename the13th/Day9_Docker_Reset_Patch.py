#!/usr/bin/env python3
import os
from pathlib import Path
import subprocess

print("🔧 Day 9 — THE13TH Docker Reset Patch (Clean Version)")

BASE = Path(__file__).resolve().parent
DOCKERFILE = BASE / "Dockerfile"
DOCKERIGNORE = BASE / ".dockerignore"
RENDER_YAML = BASE.parent / "render.yaml"  # exists one level above the13th/

def write(path: Path, content: str):
    path.write_text(content)
    print(f"✔ Wrote {path}")

# ---------------------------------------------
# 1) Remove render.yaml (if present)
# ---------------------------------------------
if RENDER_YAML.exists():
    RENDER_YAML.unlink()
    print(f"✔ Removed {RENDER_YAML}")
else:
    print("✔ render.yaml already removed")

# ---------------------------------------------
# 2) Stable Dockerfile (Render-safe)
# ---------------------------------------------
DOCKERFILE_CONTENT = """\
# -------- FRONTEND BUILD --------
FROM node:18 AS frontend
WORKDIR /app
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm install
COPY frontend ./frontend
RUN cd frontend && npm run build

# -------- BACKEND BUILD --------
FROM python:3.10-slim AS backend
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy backend source
COPY app ./app
COPY data ./data
COPY config ./config
COPY static ./static
COPY templates ./templates

# Copy built frontend
COPY --from=frontend /app/frontend/dist ./frontend/dist

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers"]
"""

write(DOCKERFILE, DOCKERFILE_CONTENT)

# ---------------------------------------------
# 3) .dockerignore
# ---------------------------------------------
DOCKERIGNORE_CONTENT = """\
__pycache__/
*.pyc
*.pyo
*.pyd
*.db
.env
.env.local
.env.*.local
node_modules/
frontend/node_modules/
.vscode/
"""

write(DOCKERIGNORE, DOCKERIGNORE_CONTENT)

# ---------------------------------------------
# 4) Commit
# ---------------------------------------------
print("🔁 Committing changes...")
subprocess.run(["git", "add", "."], cwd=BASE)
subprocess.run(["git", "commit", "-m", "fix(day9): stable Dockerfile reset"], cwd=BASE)

print("🎯 Day 9 Reset Patch applied successfully.")
