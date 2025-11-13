#!/usr/bin/env python3
"""
Day 9 — Dockerfile Auto-Fix Script for THE13TH
- Cleans broken COPY instruction
- Rewrites Dockerfile to known-good production form
- Commits + pushes automatically
- Triggers Render deploy
"""

import os
import subprocess
import logging
from datetime import datetime, timezone
from pathlib import Path
import requests

# ----------------------------------------
# Config
# ----------------------------------------
REPO_ROOT = Path(__file__).resolve().parent
DOCKERFILE = REPO_ROOT / "Dockerfile"
BACKUP = REPO_ROOT / f"Dockerfile.bak.{datetime.now(timezone.utc).timestamp()}"

RENDER_DEPLOY_HOOK = (
    "https://api.render.com/deploy/srv-d4a6l07gi27c739spc0g?key=ZBnxoh-Us8o"
)

# ----------------------------------------
# Logging
# ----------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


# ----------------------------------------
# Stable, Correct Dockerfile
# ----------------------------------------
FIXED_DOCKERFILE = """\
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
"""


# ----------------------------------------
# Write Dockerfile
# ----------------------------------------
def write_fixed_dockerfile():
    if DOCKERFILE.exists():
        logging.info(f"Backing up existing Dockerfile → {BACKUP}")
        DOCKERFILE.rename(BACKUP)

    logging.info("Writing corrected Day 9 Dockerfile")
    DOCKERFILE.write_text(FIXED_DOCKERFILE)


# ----------------------------------------
# Git commit + push
# ----------------------------------------
def git_commit_and_push():
    try:
        subprocess.run(
            ["git", "add", "Dockerfile"],
            cwd=REPO_ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        msg = f"fix: Day 9 Dockerfile stability patch — {datetime.now(timezone.utc).isoformat()}"
        subprocess.run(
            ["git", "commit", "-m", msg],
            cwd=REPO_ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        subprocess.run(
            ["git", "push"],
            cwd=REPO_ROOT,
            check=True,
        )

        logging.info("✅ Git push successful.")
        return True

    except subprocess.CalledProcessError as e:
        logging.error(f"Git error: {e}")
        return False


# ----------------------------------------
# Trigger Render Deploy
# ----------------------------------------
def trigger_render_deploy():
    logging.info(f"🚀 Triggering Render deploy: {RENDER_DEPLOY_HOOK}")
    try:
        r = requests.post(RENDER_DEPLOY_HOOK, timeout=10)
        logging.info(f"Render deploy result: {r.text}")
    except Exception as e:
        logging.error(f"Deploy hook failed: {e}")


# ----------------------------------------
# Main
# ----------------------------------------
def main():
    logging.info("Starting Day 9: Dockerfile Autofix Script")

    write_fixed_dockerfile()

    if git_commit_and_push():
        trigger_render_deploy()
    else:
        logging.warning("⚠️ Git push failed — no deploy triggered.")

    logging.info("Day 9 Dockerfile autofix complete.")


if __name__ == "__main__":
    main()
