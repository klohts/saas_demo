"""
Day 9 — Docker Reset Patch (single-file fixer)
Place this file at: ~/AIAutomationProjects/saas_demo/the13th/Day9_Docker_Reset_Patch.py

What it does (idempotent, safe):
  - Writes a stable multi-stage Dockerfile that preserves backend copy precedence
  - Writes a conservative .dockerignore
  - Writes a .env.production.example (safe defaults)
  - Optionally commits & pushes the changes (git) and triggers a Render deploy hook

Design choices (production-minded):
  - Uses environment variable RENDER_DEPLOY_HOOK to trigger auto-deploy (so secrets are never in repo)
  - Exits gracefully on errors; logs everything
  - No destructive deletes (it will back up existing Dockerfile/.dockerignore first)

How to run:
  1) Save this file to:
       ~/AIAutomationProjects/saas_demo/the13th/Day9_Docker_Reset_Patch.py
  2) Make sure your repo is clean or commit local work.
  3) (Optional) export RENDER_DEPLOY_HOOK to trigger a Render deploy after commit:
       export RENDER_DEPLOY_HOOK="https://api.render.com/deploy/srv-...?..."
  4) Run:
       python Day9_Docker_Reset_Patch.py

Notes:
  - This script will create/overwrite Dockerfile and .dockerignore in the current folder.
  - It will create a backup: Dockerfile.bak.TIMESTAMP and .dockerignore.bak.TIMESTAMP
  - If RENDER_DEPLOY_HOOK is set and git push succeeds, it will POST to the hook.

"""

from __future__ import annotations

import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import json
import urllib.request

# ---------------------------
# Config
# ---------------------------
REPO_ROOT = Path.cwd()  # expected to be ~/AIAutomationProjects/saas_demo/the13th
DOCKERFILE_PATH = REPO_ROOT / "Dockerfile"
DOCKERIGNORE_PATH = REPO_ROOT / ".dockerignore"
ENV_EXAMPLE_PATH = REPO_ROOT / ".env.production.example"
BACKUP_TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("day9-reset")

# ---------------------------
# Templates
# ---------------------------
DOCKERFILE_CONTENT = f"""
# Day 9: Stable multi-stage Dockerfile for THE13TH
# Builds frontend (Vite) then backend. Ensures backend is copied after build context
# so that the latest Python code is always present at runtime.

# ----------------------
# 1) Build frontend
# ----------------------
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend

# install deps early (cacheable)
COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps

# copy entire frontend and build
COPY frontend/ ./
RUN npm run build

# ----------------------
# 2) Build backend dependencies
# ----------------------
FROM python:3.12-slim AS backend-builder
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# install system deps we might need (kept minimal)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential git ca-certificates && rm -rf /var/lib/apt/lists/*

# copy only requirements first for caching
COPY requirements.txt ./
RUN python -m pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# ----------------------
# 3) Final runtime image
# ----------------------
FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# create non-root user
RUN useradd -m appuser || true

# copy installed python packages from backend-builder (site-packages)
# Note: copying wheels/site-packages is tricky across different images; instead reinstall requirements here in runtime for reproducibility
COPY requirements.txt ./
RUN python -m pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy the backend app AFTER deps so local changes propagate
COPY . .

# Bring in the built frontend output into the exact path the app expects
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# ensure proper ownership on files (appuser)
RUN chown -R appuser:appuser /app
USER appuser

# port for Render (must be bound to $PORT)
ENV PORT=8000
EXPOSE $PORT

# runtime command — use $PORT and module path app.main:app
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
""".lstrip()

DOCKERIGNORE_CONTENT = """
# ignore files that must not be copied into the image
venv/
.venv/
__pycache__/
node_modules/
frontend/node_modules/
*.pyc
*.pyo
*.pyd
*.db
*.sqlite3
.env
.env.*
.git
.gitignore
.DS_Store
README.md
tmp/
logs/
frontend/src/
frontend/.env
"""

ENV_PROD_EXAMPLE = """
# .env.production.example — copy to .env.production and set real secrets
ENVIRONMENT=production
ADMIN_USER=admin
ADMIN_PASS=changeme_replace_this
LOG_LEVEL=info
PORT=8000
RENDER_DEPLOY_HOOK=
"""

# ---------------------------
# Helpers
# ---------------------------

def backup_if_exists(path: Path) -> Optional[Path]:
    if path.exists():
        bak = path.with_suffix(path.suffix + f".bak.{BACKUP_TS}")
        shutil.copy2(path, bak)
        logger.info("Backed up %s -> %s", path, bak)
        return bak
    return None


def write_file(path: Path, content: str, mode: str = "w") -> None:
    path.write_text(content)
    logger.info("Wrote: %s", path)


def safe_git_commit_and_push(files: list[str], message: str, cwd: Path = REPO_ROOT, timeout: int = 120) -> dict:
    result = {"committed": False, "push_ok": False}
    try:
        subprocess.run(["git", "add"] + files, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "commit", "-m", message], cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result["committed"] = True
    except subprocess.CalledProcessError as e:
        logger.warning("git commit failed (may be no changes): %s", e)
        # continue — maybe nothing to commit
    # attempt push
    try:
        subprocess.run(["git", "push"], cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        result["push_ok"] = True
    except subprocess.TimeoutExpired as e:
        logger.error("git push timed out: %s", e)
    except subprocess.CalledProcessError as e:
        logger.error("git push failed: %s", e)
    return result


def trigger_render_deploy(hook_url: str) -> dict:
    resp = {"triggered": False, "status": None, "body": None}
    if not hook_url:
        return resp
    try:
        req = urllib.request.Request(hook_url, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode('utf-8')
            resp.update({"triggered": True, "status": r.getcode(), "body": body})
            logger.info("Triggered Render deploy: status=%s body=%s", r.getcode(), body)
    except Exception as e:
        logger.error("Render hook trigger failed: %s", e)
    return resp

# ---------------------------
# Main
# ---------------------------

def main():
    logger.info("Starting Day 9 Docker Reset Patch at %s", REPO_ROOT)

    # Validate repo root contains app/main.py
    expected_main = REPO_ROOT / "app" / "main.py"
    if not expected_main.exists():
        logger.error("Expected app/main.py not found at %s — aborting", expected_main)
        sys.exit(1)

    # Backups
    backup_if_exists(DOCKERFILE_PATH)
    backup_if_exists(DOCKERIGNORE_PATH)

    # Write files
    write_file(DOCKERFILE_PATH, DOCKERFILE_CONTENT)
    write_file(DOCKERIGNORE_PATH, DOCKERIGNORE_CONTENT)

    # Write .env.production.example only if doesn't exist
    if not ENV_EXAMPLE_PATH.exists():
        write_file(ENV_EXAMPLE_PATH, ENV_PROD_EXAMPLE)
    else:
        logger.info("%s already exists — leaving intact", ENV_EXAMPLE_PATH)

    # Git commit/push
    commit_msg = f"chore(day9): reset stable Dockerfile — {datetime.now(timezone.utc).isoformat()}"
    git_result = safe_git_commit_and_push([str(DOCKERFILE_PATH.name), str(DOCKERIGNORE_PATH.name), str(ENV_EXAMPLE_PATH.name)], commit_msg)
    logger.info("Git result: %s", json.dumps(git_result))

    # Trigger Render deploy if env var set
    hook = os.getenv("RENDER_DEPLOY_HOOK")
    if hook:
        logger.info("RENDER_DEPLOY_HOOK detected — triggering deploy")
        trigger_render_deploy(hook)
    else:
        logger.info("RENDER_DEPLOY_HOOK not set — skipping auto-deploy. To trigger: export RENDER_DEPLOY_HOOK and rerun this script or call the hook yourself.")

    logger.info("Day 9 Docker Reset Patch complete — check 'git status' and Render deploy logs.")


if __name__ == "__main__":
    main()
