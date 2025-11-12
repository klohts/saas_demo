#!/usr/bin/env python3
"""
create_render_tenant_onboarding_bundle.py

Single-file Day 7 bundle generator for THE13TH — Multi-tenant onboarding (SQLite)
Creates tenant onboarding router, sqlite DB, per-tenant config folders, .env.production example,
README_RENDER_TENANTS.md, updates .gitignore, commits & pushes, and triggers Render deploy hook.

Save to: ~/AIAutomationProjects/saas_demo/the13th/create_render_tenant_onboarding_bundle.py
Run: python create_render_tenant_onboarding_bundle.py

Requirements (for running this script locally):
- Python 3.11+/3.12
- requests

This script is idempotent and non-destructive; it will skip files that already exist.
Environment variables used (preferred, no hard-coded secrets):
- RENDER_DEPLOY_HOOK  (e.g. https://api.render.com/deploy/...?key=...)
- TENANTS_DB_PATH     (optional; defaults to ./data/tenants.db)

Behavior summary:
- Creates data/tenants.db and tenants table
- Writes app/tenants.py (FastAPI router) that can be mounted by your main app
- Creates config/tenants/<tenant_id>/customization.json for new tenants
- Commits changes and attempts git push (timeout handled)
- POSTs to the Render hook (if provided) to trigger redeploy

Author: Ken (with ChatGPT)
"""

from __future__ import annotations

import os
import sys
import json
import sqlite3
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import secrets

try:
    import requests
except Exception:
    requests = None  # script will still write files; network ops will raise clear error if attempted

# -----------------------------
# Configuration
# -----------------------------
REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR = REPO_ROOT / "data"
CONFIG_DIR = REPO_ROOT / "config" / "tenants"
APP_DIR = REPO_ROOT / "app"
TENANTS_DB = Path(os.getenv("TENANTS_DB_PATH", DATA_DIR / "tenants.db"))
RENDER_HOOK = os.getenv("RENDER_DEPLOY_HOOK", os.getenv("RENDER_DEPLOY_HOOK_URL", ""))
GIT_AUTHOR_NAME = os.getenv("GIT_AUTHOR_NAME", "automation-bot")
GIT_AUTHOR_EMAIL = os.getenv("GIT_AUTHOR_EMAIL", "automation@local")

# Files to create
ROUTER_FILE = APP_DIR / "tenants.py"
ENV_EXAMPLE = REPO_ROOT / ".env.production"
README_FILE = REPO_ROOT / "README_RENDER_TENANTS.md"
GITIGNORE = REPO_ROOT / ".gitignore"

# -----------------------------
# Logging
# -----------------------------
LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "day7_tenants.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("day7")

# -----------------------------
# Helpers
# -----------------------------

def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    APP_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Ensured directories: {DATA_DIR}, {CONFIG_DIR}, {APP_DIR}")


def init_db(db_path: Path) -> None:
    """Create tenants table if it doesn't exist."""
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tenants (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                api_key TEXT NOT NULL UNIQUE,
                config_path TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
        logger.info(f"Initialized tenants DB at {db_path}")
    finally:
        conn.close()


def write_env_example(path: Path, db_path: Path, render_hook: str) -> None:
    if path.exists():
        logger.info(f"Skipping existing env example: {path}")
        return
    content = (
        f"# Production env for THE13TH — Tenants bundle\n"
        f"TENANTS_DB_PATH={db_path}\n"
        f"# Render deploy hook (set in env when running this script or in CI)\n"
        f"RENDER_DEPLOY_HOOK={render_hook or 'https://api.render.com/deploy/<service>?key=<KEY>'}\n"
    )
    path.write_text(content)
    logger.info(f"Wrote env example to {path}")


def write_router_file(path: Path, db_path: Path) -> None:
    if path.exists():
        logger.info(f"Skipping existing router file: {path}")
        return

    content = f'''"""
FastAPI router for tenant onboarding (auto-generated).
Mount in your main app with: `from app.tenants import router as tenants_router` then
`app.include_router(tenants_router, prefix="/api/tenants")`.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict
from datetime import datetime, timezone
import secrets
import json
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

DB_PATH = Path(r"{db_path}")
CONFIG_ROOT = Path("{CONFIG_DIR}")

router = APIRouter(tags=["tenants"])


class TenantCreate(BaseModel):
    name: str


class TenantOut(BaseModel):
    id: str
    name: str
    api_key: str
    config_path: str
    created_at: str


def _get_conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    return conn


@router.post("/", response_model=TenantOut, status_code=201)
async def create_tenant(payload: TenantCreate):
    """Create a tenant, generate API key, create config folder and persist to SQLite."""
    tenant_id = secrets.token_urlsafe(8)
    api_key = secrets.token_urlsafe(32)
    created_at = datetime.now(timezone.utc).isoformat()
    tenant_dir = CONFIG_ROOT / tenant_id
    tenant_dir.mkdir(parents=True, exist_ok=True)
    customization = {{
        "tenant_id": tenant_id,
        "name": payload.name,
        "theme": {{"primary": "#4F46E5", "accent": "#06B6D4"}},
        "branding": {{"logo": "", "company": payload.name}},
    }}
    config_path = tenant_dir / "customization.json"
    config_path.write_text(json.dumps(customization, indent=2))

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tenants (id, name, api_key, config_path, created_at) VALUES (?, ?, ?, ?, ?)",
            (tenant_id, payload.name, api_key, str(config_path), created_at),
        )
        conn.commit()
    finally:
        conn.close()

    return TenantOut(id=tenant_id, name=payload.name, api_key=api_key, config_path=str(config_path), created_at=created_at)


@router.get("/", response_model=list[TenantOut])
async def list_tenants():
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, api_key, config_path, created_at FROM tenants ORDER BY created_at DESC")
        rows = cur.fetchall()
        return [TenantOut(id=r[0], name=r[1], api_key=r[2], config_path=r[3], created_at=r[4]) for r in rows]
    finally:
        conn.close()


@router.get("/{{tenant_id}}", response_model=TenantOut)
async def get_tenant(tenant_id: str):
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, api_key, config_path, created_at FROM tenants WHERE id = ?", (tenant_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
        return TenantOut(id=row[0], name=row[1], api_key=row[2], config_path=row[3], created_at=row[4])
    finally:
        conn.close()
'''
    path.write_text(content)
    logger.info(f"Wrote router file to {path}")


def write_readme(path: Path) -> None:
    """Create README with instructions for tenant onboarding if not already present."""
    if path.exists():
        logger.info(f"Skipping existing README: {path}")
        return
    content = """# THE13TH — Tenant Onboarding (SQLite)

This README documents the multi-tenant onboarding bundle generated by create_render_tenant_onboarding_bundle.py.

What this adds:
- SQLite database at data/tenants.db with a tenants table
- FastAPI router at app/tenants.py
- Per-tenant config folders under config/tenants/<tenant_id>/ with customization.json
- .env.production example with TENANTS_DB_PATH and RENDER_DEPLOY_HOOK
- Optional Render deploy hook trigger after commit/push

How to use:
1) Mount the router in your FastAPI app:
   from app.tenants import router as tenants_router
   app.include_router(tenants_router, prefix="/api/tenants")

2) Endpoints:
   - POST /api/tenants/
     Body: { "name": "<Tenant Name>" }
     Creates a tenant, generates an API key, creates config folder and customization.json, and persists to SQLite.
   - GET /api/tenants/
     Lists all tenants (most recent first).
   - GET /api/tenants/{tenant_id}
     Gets a single tenant.

3) Environment:
   - TENANTS_DB_PATH points to the SQLite DB (defaults to ./data/tenants.db)
   - RENDER_DEPLOY_HOOK can be used to trigger a Render deploy

Notes:
- The script is idempotent and will not overwrite existing files it created, unless you remove them first.
- Make sure to commit and push changes; the script attempts this automatically and logs results in logs/day7_tenants.log.
"""
    path.write_text(content)
    logger.info(f"Wrote README to {path}")


def update_gitignore(path: Path) -> None:
    content = path.read_text() if path.exists() else ""
    additions = [".env.production", "data/*.db", "config/tenants/*/secret.key"]
    changed = False
    for a in additions:
        if a not in content:
            content += "\n" + a
            changed = True
    if changed:
        path.write_text(content)
        logger.info(f"Updated .gitignore at {path}")
    else:
        logger.info(".gitignore already contains required patterns")


def git_commit_and_push(message: str, paths: Optional[list[str]] = None, timeout: int = 20) -> dict:
    paths = paths or ["app/tenants.py", "config/tenants", "data/tenants.db", ".env.production", "README_RENDER_TENANTS.md"]
    try:
        subprocess.run(["git", "add"] + paths, cwd=REPO_ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        env = os.environ.copy()
        env.update({"GIT_AUTHOR_NAME": GIT_AUTHOR_NAME, "GIT_AUTHOR_EMAIL": GIT_AUTHOR_EMAIL})
        subprocess.run(["git", "commit", "-m", message], cwd=REPO_ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        push_proc = subprocess.run(["git", "push"], cwd=REPO_ROOT, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        logger.info(f"Git push stdout: {push_proc.stdout.decode().strip()}")
        logger.info(f"Git push stderr: {push_proc.stderr.decode().strip()}")
        return {"committed": True, "push_ok": push_proc.returncode == 0}
    except subprocess.TimeoutExpired as ex:
        logger.warning("git push timed out")
        return {"committed": True, "push_ok": False, "timeout": True}
    except subprocess.CalledProcessError as ex:
        logger.error(f"Git error: {ex}")
        return {"committed": False, "push_ok": False}


def trigger_render_hook(hook: str) -> dict:
    if not hook:
        logger.info("No render hook provided; skipping deploy trigger")
        return {"triggered": False}
    if requests is None:
        logger.error("requests library not installed; cannot trigger render hook")
        return {"triggered": False, "error": "requests_missing"}
    try:
        r = requests.post(hook, timeout=10)
        r.raise_for_status()
        logger.info(f"Render deploy triggered: {r.text}")
        return {"triggered": True, "response": r.text}
    except Exception as ex:
        logger.error(f"Render hook trigger failed: {ex}")
        return {"triggered": False, "error": str(ex)}


# -----------------------------
# Main
# -----------------------------

def main() -> None:
    logger.info("Starting Day 7: Tenant Onboarding bundle generator")
    ensure_dirs()
    init_db(TENANTS_DB)
    write_env_example(ENV_EXAMPLE, TENANTS_DB, RENDER_HOOK)
    write_router_file(ROUTER_FILE, TENANTS_DB)
    write_readme(README_FILE)
    update_gitignore(GITIGNORE)

    commit_msg = f"chore: Day7 tenant onboarding bundle — {datetime.now(timezone.utc).isoformat()}"
    git_result = git_commit_and_push(commit_msg)
    logger.info(f"Git result: {git_result}")

    render_result = trigger_render_hook(RENDER_HOOK)
    logger.info(f"Render trigger result: {render_result}")

    logger.info("Day 7 bundle generation complete. Next steps:\n"
                "1) Ensure app.main includes the router: app.include_router(tenants_router, prefix=\"/api/tenants\")\n"
                "2) Commit & push changes (already attempted)\n"
                "3) Verify endpoint: POST /api/tenants/"
                )


if __name__ == "__main__":
    main()
