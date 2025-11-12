#!/usr/bin/env python3
"""
create_render_staging_bundle.py
THE13TH — Render Staging Bundle Generator + Auto-Deploy
Creates Dockerfile, .env.production, .env.example, render.yaml, and README_RENDER.md.
Triggers Render deployment if RENDER_DEPLOY_HOOK is found or set.
"""

import os
import subprocess
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RENDER_DEPLOY_HOOK = os.getenv(
    "RENDER_DEPLOY_HOOK",
    "https://api.render.com/deploy/srv-d4a6l07gi27c739spc0g?key=ZBnxoh-Us8o",
)

FILES = {
    "Dockerfile": """# ============================================
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

RUN apt-get update && apt-get install -y --no-install-recommends \\
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
""",

    ".env.example": """# ============================================
# THE13TH — .env.example (safe to commit)
# ============================================
ENVIRONMENT=development
ADMIN_USER=admin
ADMIN_PASS=changeme
LOG_LEVEL=info
DATABASE_URL=sqlite:///data/clients.db
RATE_LIMIT_PER_MIN=100
""",

    ".env.production": f"""# ============================================
# THE13TH — .env.production (DO NOT COMMIT)
# ============================================
ENVIRONMENT=production
ADMIN_USER={{ADMIN_USER}}
ADMIN_PASS={{ADMIN_PASS}}
LOG_LEVEL=info
DATABASE_URL={{DATABASE_URL}}
RATE_LIMIT_PER_MIN=100
SMTP_HOST={{SMTP_HOST}}
SMTP_PORT={{SMTP_PORT}}
SMTP_USER={{SMTP_USER}}
SMTP_PASS={{SMTP_PASS}}
SENTRY_DSN={{SENTRY_DSN}}
RENDER_DEPLOY_HOOK={RENDER_DEPLOY_HOOK}
""",

    "README_RENDER.md": """# THE13TH — Render Staging Deployment Guide

## Steps to Deploy

1. Add `.env.production` locally (do not commit).
2. In Render Dashboard:
   - Create **Web Service**
   - Environment = **Docker**
   - Dockerfile path = `the13th/Dockerfile`
   - Build Command: *(leave empty)*
   - Start Command: *(leave empty)*

3. Add environment variables manually under **Environment**.
4. Enable Auto Deploy from GitHub → branch `main`.
5. Test health endpoint:
   ```bash
   curl -s https://the13th.onrender.com/healthz
   ```
6. Local test before pushing:
   ```bash
   docker build -t the13th:staging -f the13th/Dockerfile .
   docker run --env-file the13th/.env.example -p 8000:8000 the13th:staging
   curl http://localhost:8000/healthz
   ```
""",

    "../../render.yaml": """# ============================================
# Render Service Configuration for THE13TH
# ============================================
services:
  - type: web
    name: the13th
    env: docker
    repo: https://github.com/klohts/saas_demo
    branch: main
    dockerfilePath: the13th/Dockerfile
    plan: free
    buildCommand: ''
    startCommand: ''
    envVars:
      - key: ENVIRONMENT
        value: production
      - key: ADMIN_USER
        value: ''
"""
}


def create_files():
    for relative_path, content in FILES.items():
        file_path = BASE_DIR / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        print(f"✅ Created: {file_path.relative_to(Path.home())}")


def append_gitignore():
    gitignore_path = BASE_DIR.parent / ".gitignore"
    line = ".env.production\n"
    if gitignore_path.exists():
        with open(gitignore_path, "r+", encoding="utf-8") as f:
            content = f.read()
            if ".env.production" not in content:
                f.write("\n" + line)
                print("✅ Updated .gitignore to exclude .env.production")
    else:
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write(line)
        print("✅ Created .gitignore excluding .env.production")


def trigger_render_deploy():
    if not RENDER_DEPLOY_HOOK:
        print("⚠️  No Render deploy hook found. Skipping auto-deploy.")
        return

    print(f"🚀 Triggering Render deploy via hook: {RENDER_DEPLOY_HOOK}")
    try:
        response = requests.post(RENDER_DEPLOY_HOOK, timeout=10)
        if response.status_code == 200:
            print(f"✅ Render deployment triggered successfully. Response: {response.text}")
        else:
            print(f"⚠️  Render deploy hook returned status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Render deploy hook failed: {e}")


if __name__ == "__main__":
    print("🚀 Generating THE13TH Render Staging Bundle...\n")
    create_files()
    append_gitignore()
    trigger_render_deploy()
    print("\n🎯 Bundle creation complete!")
    print("Next steps:")
    print("1️⃣ Review files under ~/AIAutomationProjects/saas_demo/the13th/")
    print("2️⃣ Commit and push to GitHub")
    print("3️⃣ Verify Render auto-deployment at https://the13th.onrender.com/healthz")
