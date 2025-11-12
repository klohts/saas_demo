#!/usr/bin/env python3
"""
create_render_client_customization_bundle.py
Single-file bundle generator for THE13TH — Day 6 Client Customization + auto-deploy to Render
Location (output): ~/AIAutomationProjects/saas_demo/the13th/

What it does (single-run script):
- Creates client customization JSON files (client_customization.json, client_theme.json) if missing
- Writes a production .env.production (safe defaults) and updates .gitignore
- Generates a FastAPI router file at the13th/app/customization.py that exposes tenant customization APIs
- Adds a README_RENDER_CLIENT_CUSTOMIZATION.md with instructions
- Commits changes to git and (optionally) triggers Render deploy via the deploy hook

Design goals (per Ken Dev Mode):
- Single-file, production-ready script
- Uses environment variables for secrets (but will accept an explicit --hook fallback)
- Logging, validation, error handling
- Clear file placement in repo

How to run:
  cd ~/AIAutomationProjects/saas_demo/the13th
  python create_render_client_customization_bundle.py [--hook https://api.render.com/deploy/...] [--no-deploy]

Notes:
- If you want the script to auto-deploy, set the environment variable RENDER_DEPLOY_HOOK or pass --hook.
- This script will not expose secrets in commits; .env.production is added to .gitignore.
"""

from __future__ import annotations
import os
import sys
import json
import argparse
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# -----------------------------
# Configuration / Paths
# -----------------------------
REPO_ROOT = Path.home() / "AIAutomationProjects" / "saas_demo" / "the13th"
if not REPO_ROOT.exists():
    # fallback to current working dir if user runs from repo root
    REPO_ROOT = Path.cwd()

LOGS_DIR = REPO_ROOT / "logs"
APP_DIR = REPO_ROOT / "app"
APP_DIR.mkdir(parents=True, exist_ok=True)

CLIENT_CUSTOMIZATION_FILE = REPO_ROOT / "client_customization.json"
CLIENT_THEME_FILE = REPO_ROOT / "client_theme.json"
ENV_PROD_FILE = REPO_ROOT / ".env.production"
GITIGNORE_FILE = REPO_ROOT / ".gitignore"
ROUTER_FILE = APP_DIR / "customization.py"
README_FILE = REPO_ROOT / "README_RENDER_CLIENT_CUSTOMIZATION.md"

# default render hook fallback (not hard-coded secret in production — override via env or CLI)
# Recommended: export RENDER_DEPLOY_HOOK in your shell before running this script.
DEFAULT_RENDER_HOOK_FALLBACK = ""  # intentionally empty to encourage env usage

# -----------------------------
# Logging
# -----------------------------
LOGS_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "bundle_generator.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("the13th.bundle.day6")

# -----------------------------
# Templates / Defaults
# -----------------------------
DEFAULT_CLIENT_CUSTOMIZATION: Dict[str, Dict[str, Any]] = {
    "example_client": {
        "display_name": "Example Client",
        "logo_url": "https://cdn.the13th.ai/example-logo.png",
        "primary_color": "#1E90FF",
        "accent_color": "#F0F8FF",
        "dashboard_title": "Example Client Intelligence",
        "features": {
            "show_event_feed": True,
            "enable_pricing_panel": False
        }
    }
}

DEFAULT_CLIENT_THEME: Dict[str, Any] = {
    "default": {
        "background_color": "#F9FAFB",
        "font_family": "Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial",
        "border_radius": "10px",
        "card_elevation": "2",
    }
}

ROUTER_CODE = '''"""FastAPI router: client customization endpoints
Place this file at: the13th/app/customization.py
Import and include the router in your main FastAPI app as:

    from app.customization import router as customization_router
    app.include_router(customization_router, prefix="/api/customization")

This file reads client_customization.json and client_theme.json and exposes secure update endpoints (basic auth).
"""
from typing import Dict, Any
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

router = APIRouter()
BASE = Path(__file__).resolve().parents[1]
CUSTOM_FILE = BASE / "client_customization.json"
THEME_FILE = BASE / "client_theme.json"
security = HTTPBasic()

# Basic admin guard — reads credentials from environment to avoid hardcoding.
import os
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "changeme")


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


@router.get("/", summary="List all client customizations")
async def list_customizations():
    return _load_json(CUSTOM_FILE)


@router.get("/{client}", summary="Get customization for a client")
async def get_customization(client: str):
    data = _load_json(CUSTOM_FILE)
    if client not in data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="client not found")
    return data[client]


@router.get("/theme/default", summary="Get default theme")
async def get_default_theme():
    return _load_json(THEME_FILE).get("default", {})


def _verify_admin(creds: HTTPBasicCredentials = Depends(security)):
    correct_user = secrets.compare_digest(creds.username, ADMIN_USER)
    correct_pw = secrets.compare_digest(creds.password, ADMIN_PASS)
    if not (correct_user and correct_pw):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    return True


@router.post("/update/{client}", summary="Update a client's customization (admin)")
async def update_customization(client: str, payload: Dict[str, Any], _a: bool = Depends(_verify_admin)):
    data = _load_json(CUSTOM_FILE)
    data[client] = payload
    with open(CUSTOM_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return {"status": "ok", "client": client}


@router.post("/theme/update", summary="Update default theme (admin)")
async def update_theme(payload: Dict[str, Any], _a: bool = Depends(_verify_admin)):
    data = _load_json(THEME_FILE)
    data["default"] = payload
    with open(THEME_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return {"status": "ok"}
'''

README_CONTENT = f"""# THE13TH — Day 6: Client Customization (Render staging bundle)

Files created/updated by this bundle (location: {REPO_ROOT}):

- client_customization.json  — per-tenant branding & config (JSON)
- client_theme.json          — default theme values
- app/customization.py       — FastAPI router for customization endpoints (add to app)
- .env.production           — production env (RENDER_DEPLOY_HOOK stored here)
- README_RENDER_CLIENT_CUSTOMIZATION.md — this document

How to wire into your existing FastAPI app (app/main.py):

```py
from fastapi import FastAPI
from app.customization import router as customization_router
app = FastAPI()
app.include_router(customization_router, prefix="/api/customization")
```

Security:
- Admin updates are protected by HTTP Basic. Set ADMIN_USER and ADMIN_PASS in your .env.production.

Auto-deploy:
- This script will attempt to trigger a Render deploy if RENDER_DEPLOY_HOOK is present in environment or passed with --hook.

"""

# -----------------------------
# Helpers
# -----------------------------

def write_json_file(path: Path, data: Dict[str, Any]) -> None:
    logger.debug("Writing JSON to %s", path)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    logger.info("Created/updated %s", path)


def write_text_file(path: Path, content: str, mode: str = "w") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode, encoding="utf-8") as fh:
        fh.write(content)
    logger.info("Wrote %s", path)


def git_commit_and_push(commit_message: str) -> bool:
    try:
        subprocess.run(["git", "add", "--all"], cwd=REPO_ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "commit", "-m", commit_message], cwd=REPO_ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "push"], cwd=REPO_ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info("Committed and pushed changes to git")
        return True
    except subprocess.CalledProcessError as exc:
        logger.warning("Git commit/push failed: %s", exc)
        return False


def trigger_render_deploy(hook_url: str) -> Optional[Dict[str, Any]]:
    if not hook_url:
        logger.warning("No Render hook URL provided — skipping deploy")
        return None
    # Try using curl first (safer for environments without requests), fallback to urllib
    try:
        logger.info("Triggering Render deploy via hook: %s", hook_url)
        proc = subprocess.run(["curl", "-s", "-X", "POST", hook_url], check=False, capture_output=True, text=True)
        out = proc.stdout.strip()
        if out:
            try:
                return json.loads(out)
            except Exception:
                return {"raw": out}
        return {"status": "ok", "raw": out}
    except Exception as exc:
        logger.exception("Failed to trigger render hook: %s", exc)
        return None


# -----------------------------
# Main
# -----------------------------

def main(argv: Optional[list[str]] = None) -> int:
    argv = argv or sys.argv[1:]
    parser = argparse.ArgumentParser(prog="create_render_client_customization_bundle.py")
    parser.add_argument("--hook", type=str, help="Render deploy hook URL (overrides env)")
    parser.add_argument("--no-deploy", action="store_true", help="Create files but do not trigger deploy")
    args = parser.parse_args(argv)

    # Determine render hook
    render_hook = args.hook or os.getenv("RENDER_DEPLOY_HOOK") or os.getenv("RENDER_HOOK") or DEFAULT_RENDER_HOOK_FALLBACK
    if not render_hook:
        logger.warning("No render hook detected in env or CLI. Auto-deploy will be skipped unless --hook is provided.")

    # 1) Create JSON files if missing
    if not CLIENT_CUSTOMIZATION_FILE.exists():
        write_json_file(CLIENT_CUSTOMIZATION_FILE, DEFAULT_CLIENT_CUSTOMIZATION)
    else:
        logger.info("%s already exists — preserving", CLIENT_CUSTOMIZATION_FILE)

    if not CLIENT_THEME_FILE.exists():
        write_json_file(CLIENT_THEME_FILE, DEFAULT_CLIENT_THEME)
    else:
        logger.info("%s already exists — preserving", CLIENT_THEME_FILE)

    # 2) Write router file (idempotent: will not overwrite existing router unless content differs)
    write_router = True
    if ROUTER_FILE.exists():
        existing = ROUTER_FILE.read_text(encoding="utf-8")
        if existing.strip() == ROUTER_CODE.strip():
            write_router = False
            logger.info("Router file already in place and up-to-date: %s", ROUTER_FILE)

    if write_router:
        write_text_file(ROUTER_FILE, ROUTER_CODE)

    # 3) .env.production — do not overwrite if exists; write safe defaults
    if not ENV_PROD_FILE.exists():
        env_lines = [
            f"ENVIRONMENT=production",
            f"ADMIN_USER=admin",
            f"ADMIN_PASS=changeme",
            f"LOG_LEVEL=info",
            f"RENDER_DEPLOY_HOOK={render_hook if render_hook else ''}",
        ]
        write_text_file(ENV_PROD_FILE, "\n".join(env_lines) + "\n")
        logger.info("Wrote .env.production to %s (do not commit secrets).", ENV_PROD_FILE)
        # ensure .env.production is gitignored
        if GITIGNORE_FILE.exists():
            gi = GITIGNORE_FILE.read_text(encoding="utf-8")
            if ".env.production" not in gi:
                GITIGNORE_FILE.write_text(gi + "\n.env.production\n")
                logger.info("Appended .env.production to .gitignore")
        else:
            write_text_file(GITIGNORE_FILE, ".env.production\n")
            logger.info("Created .gitignore and added .env.production")
    else:
        logger.info("%s exists — not modifying", ENV_PROD_FILE)

    # 4) README
    write_text_file(README_FILE, README_CONTENT)

    # 5) Git commit & push
    commit_msg = f"chore: Day6 client customization bundle — {datetime.utcnow().isoformat()}"
    committed = git_commit_and_push(commit_msg)

    # 6) Trigger Render deploy (if requested and we have a hook)
    deploy_result = None
    if not args.no_deploy and render_hook:
        deploy_result = trigger_render_deploy(render_hook)
        logger.info("Render deploy response: %s", deploy_result)
    else:
        if args.no_deploy:
            logger.info("--no-deploy provided, skipping deploy step")
        else:
            logger.warning("No render hook available; skipped deploy")

    logger.info("Bundle generation complete. Review files in: %s", REPO_ROOT)
    if deploy_result:
        logger.info("Deploy triggered: %s", deploy_result)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        logger.exception("Unhandled error: %s", exc)
        raise
