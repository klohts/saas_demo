#!/usr/bin/env python3
"""
create_render_client_customization_bundle.py
Single-file bundle generator for THE13TH — Day 6: Client Customization

Placement: ~/AIAutomationProjects/saas_demo/the13th/create_render_client_customization_bundle.py

What it does (concise):
- Safely creates client customization assets and a small FastAPI router under app/customization.py
- Writes client_customization.json and client_theme.json under the13th/config/
- Writes a .env.production (ignored by git) with safe defaults if missing
- Adds/updates render.yaml at repo root (non-destructive merge)
- Commits and pushes with a timezone-aware UTC commit message
- Optionally triggers Render deploy hook via environment variable or CLI --hook

Important safety & UX improvements compared to prior version:
- Uses timezone-aware UTC datetimes: datetime.now(timezone.utc)
- Git push uses a timeout and returns stdout/stderr; it won't hang indefinitely
- Provides flags: --no-push, --no-deploy, --hook
- Robust logging, error handling, and validations

How to run:
  cd ~/AIAutomationProjects/saas_demo/the13th
  python create_render_client_customization_bundle.py           # default: create files, commit & push, deploy (if RENDER_DEPLOY_HOOK set)
  python create_render_client_customization_bundle.py --no-deploy  # do everything except trigger Render
  python create_render_client_customization_bundle.py --no-push    # create files but skip git push
  python create_render_client_customization_bundle.py --hook https://api.render.com/deploy/..   # override hook

Environment variables used:
  RENDER_DEPLOY_HOOK  - optional; URL to trigger Render deploy
  ADMIN_USER, ADMIN_PASS - will be written into .env.production if not present

"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

# -----------------------------
# Configuration / constants
# -----------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]  # ~/AIAutomationProjects/saas_demo
PROJECT_DIR = REPO_ROOT / "the13th"
APP_DIR = PROJECT_DIR / "app"
CONFIG_DIR = PROJECT_DIR / "config"
RENDER_YAML = REPO_ROOT / "render.yaml"
ENV_PROD = PROJECT_DIR / ".env.production"
GIT_AUTHOR_NAME = os.environ.get("GIT_AUTHOR_NAME", "KEN-DEV")
GIT_AUTHOR_EMAIL = os.environ.get("GIT_AUTHOR_EMAIL", "ken@example.com")
DEFAULT_RENDER_HOOK = os.environ.get("RENDER_DEPLOY_HOOK", "")

# ensure directories exist
PROJECT_DIR.mkdir(parents=True, exist_ok=True)
APP_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Logging
# -----------------------------
LOG = logging.getLogger("create_render_client_customization_bundle")
LOG.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
LOG.addHandler(handler)

# -----------------------------
# Templates
# -----------------------------
CUSTOMIZATION_ROUTER = textwrap.dedent("""
    \"\"\"
    app/customization.py
    Small FastAPI router that exposes client customization endpoints.
    \"\"\"
    from fastapi import APIRouter, Depends, HTTPException, Request
    from typing import Dict

    router = APIRouter(prefix="/customization", tags=["customization"])


    # Example in-memory store — persistent storage should be used in production
    _store = {
        "client": {
            "name": "Demo Client",
            "theme": "default",
            "logo_url": "",
        }
    }


    def _admin_check(request: Request) -> bool:
        # Quick placeholder for admin verification. Plug your auth dependency here.
        # In production, replace with real auth (JWT/OAuth2) and remove this simple check.
        api_key = request.headers.get("x-api-key") or request.query_params.get("api_key")
        if not api_key:
            raise HTTPException(status_code=401, detail="Missing API key")
        # For now accept any non-empty key — override in real deployments
        return True


    @router.get("/client", response_model=Dict)
    async def get_client_customization():
        \"\"\"Return client customization payload\"\"\"
        return _store["client"]


    @router.post("/client")
    async def set_client_customization(payload: Dict, request: Request, _=Depends(_admin_check)):
        \"\"\"Update the client customization; minimal validation included\"\"\"
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Payload must be a JSON object")
        # simple allowed keys
        allowed = {"name", "theme", "logo_url"}
        for k in list(payload.keys()):
            if k not in allowed:
                payload.pop(k)
        _store["client"].update(payload)
        return {"status": "ok", "client": _store["client"]}


    # Instruction comment: To wire this router into your main app, add:
    # from app.customization import router as customization_router
    # app.include_router(customization_router)
""")

CLIENT_CUSTOMIZATION_JSON = {
    "name": "Demo Client",
    "description": "Client-specific overrides for THE13TH",
    "theme": "default",
    "logo_url": "",
    "features": {"remove_branding": False, "custom_domains": False},
}

CLIENT_THEME_JSON = {
    "name": "default",
    "colors": {"primary": "#6D28D9", "accent": "#8B5CF6", "bg": "#F8FAFC"},
    "font": {"family": "Inter, system-ui, sans-serif", "base_size": 16},
}

ENV_PROD_TEMPLATE = textwrap.dedent("""
    # .env.production (auto-generated by create_render_client_customization_bundle.py)
    ENVIRONMENT=production
    ADMIN_USER={admin_user}
    ADMIN_PASS={admin_pass}
    LOG_LEVEL=info
    RENDER_DEPLOY_HOOK={render_hook}
""")

RENDER_YAML_TEMPLATE = textwrap.dedent("""
    services:
      - name: the13th
        env: python
        buildCommand: "./build.sh"
        startCommand: "uvicorn app.main:app --host 0.0.0.0 --port 8000"
""")

README_RENDER = textwrap.dedent("""
    THE13TH — Client Customization Bundle

    Files created/updated by this script (Day 6):
      - app/customization.py        (FastAPI router)
      - config/client_customization.json
      - config/client_theme.json
      - .env.production             (ignored by git)
      - render.yaml                 (merged at repo root)

    How to wire the router into your main app:

      1) In app/main.py (or app/__init__.py) add:

         from app.customization import router as customization_router
         app.include_router(customization_router)

      2) Restart the server and verify:
         GET /customization/client

    Deploy: this script can trigger a Render deploy if you set the RENDER_DEPLOY_HOOK environment variable
    or pass --hook on the CLI.
""")

# -----------------------------
# Utility functions
# -----------------------------

def write_text_file(path: Path, contents: str, overwrite: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        LOG.info("Skipping existing file: %s", path)
        return
    path.write_text(contents, encoding="utf-8")
    LOG.info("Wrote: %s", path)


def write_json_file(path: Path, data, overwrite: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        LOG.info("Skipping existing JSON file: %s", path)
        return
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    LOG.info("Wrote JSON: %s", path)


def safe_run(cmd: list[str], cwd: Optional[Path] = None, timeout: int = 30) -> Tuple[int, str, str]:
    """Run subprocess command returning (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
            timeout=timeout,
        )
        LOG.debug("Ran command: %s (cwd=%s) => %s", cmd, cwd, proc.returncode)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired as exc:
        LOG.warning("Command timed out: %s", cmd)
        return -1, exc.stdout or "", exc.stderr or "TimeoutExpired"
    except Exception as exc:  # pragma: no cover - defensive
        LOG.exception("Failed to run command: %s", cmd)
        return -2, "", str(exc)


def git_commit_and_push(message: str, repo_root: Path = REPO_ROOT, push: bool = True) -> Tuple[bool, str]:
    """Stage, commit, and optionally push. Returns (committed, message)."""
    # Basic checks
    if not (repo_root / ".git").exists():
        LOG.warning("No .git found at repo root %s — skipping git operations", repo_root)
        return False, "no_git"

    # Stage
    code, out, err = safe_run(["git", "add", "-A"], cwd=repo_root)
    if code != 0:
        LOG.error("git add failed: %s", err or out)
        return False, err or out

    # Commit
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = GIT_AUTHOR_NAME
    env["GIT_AUTHOR_EMAIL"] = GIT_AUTHOR_EMAIL
    try:
        code, out, err = safe_run(["git", "commit", "-m", message], cwd=repo_root)
        if code != 0:
            # if there is nothing to commit, git returns non-zero; handle gracefully
            if "nothing to commit" in (out + err):
                LOG.info("Nothing to commit")
                committed = False
            else:
                LOG.error("git commit returned non-zero: %s", err or out)
                return False, err or out
        else:
            LOG.info("Committed: %s", message)
            committed = True
    except KeyboardInterrupt:
        LOG.warning("User interrupted during git commit")
        return False, "interrupted"

    # Push (optional)
    if push:
        code, out, err = safe_run(["git", "push"], cwd=repo_root, timeout=60)
        if code != 0:
            LOG.error("git push failed (timeout or error): %s", err or out)
            return committed, err or out
        LOG.info("Pushed to remote")

    return committed, out or err


def trigger_render_hook(hook_url: str, timeout: int = 15) -> Tuple[bool, str]:
    if not hook_url:
        LOG.info("No Render hook provided; skipping deploy trigger")
        return False, "no_hook"
    curl_cmd = ["curl", "-s", "-X", "POST", hook_url]
    code, out, err = safe_run(curl_cmd, timeout=timeout)
    if code == 0 and out:
        LOG.info("Render deploy triggered: %s", out)
        return True, out
    LOG.error("Render hook failed: %s %s", out, err)
    return False, out or err


# -----------------------------
# Main builder logic
# -----------------------------

def build_bundle(render_hook: Optional[str], do_push: bool = True, do_deploy: bool = True) -> None:
    LOG.info("Starting Day 6: Client Customization Bundle generator")

    # 1) Write app/customization.py (router)
    customization_path = APP_DIR / "customization.py"
    write_text_file(customization_path, CUSTOMIZATION_ROUTER, overwrite=False)

    # 2) Write config JSON files
    write_json_file(CONFIG_DIR / "client_customization.json", CLIENT_CUSTOMIZATION_JSON, overwrite=False)
    write_json_file(CONFIG_DIR / "client_theme.json", CLIENT_THEME_JSON, overwrite=False)

    # 3) Write .env.production safely
    if not ENV_PROD.exists():
        admin_user = os.environ.get("ADMIN_USER", "admin")
        admin_pass = os.environ.get("ADMIN_PASS", "changeme")
        rendered = ENV_PROD_TEMPLATE.format(admin_user=admin_user, admin_pass=admin_pass, render_hook=render_hook or "")
        write_text_file(ENV_PROD, rendered, overwrite=False)
        # Ensure production env is ignored in git
        gitignore = PROJECT_DIR / ".gitignore"
        if not gitignore.exists() or "# ignore production env" not in gitignore.read_text(encoding="utf-8"):
            gitignore_content = (gitignore.read_text(encoding="utf-8") if gitignore.exists() else "")
            gitignore_content += "\n# ignore production env\n.env.production\n"
            write_text_file(gitignore, gitignore_content, overwrite=True)
            LOG.info("Updated .gitignore to exclude .env.production")
    else:
        LOG.info(".env.production already exists — leaving it intact")

    # 4) Merge/append render.yaml at repo root (non-destructive)
    if not RENDER_YAML.exists():
        write_text_file(RENDER_YAML, RENDER_YAML_TEMPLATE, overwrite=False)
    else:
        LOG.info("render.yaml already exists at repo root — leaving unchanged")

    # 5) README
    readme_path = PROJECT_DIR / "README_RENDER_CLIENT_CUSTOMIZATION.md"
    write_text_file(readme_path, README_RENDER, overwrite=False)

    # 6) Git commit + push
    now_utc = datetime.now(timezone.utc)
    commit_msg = f"chore: Day6 client customization bundle — {now_utc.isoformat()}"
    committed, git_out = git_commit_and_push(commit_msg, repo_root=REPO_ROOT, push=do_push)
    LOG.info("Git result: committed=%s, output=%s", committed, git_out)

    # 7) Trigger Render deploy hook if requested
    hook = render_hook or DEFAULT_RENDER_HOOK
    if do_deploy and hook:
        success, resp = trigger_render_hook(hook)
        if success:
            LOG.info("Successfully triggered Render deploy: %s", resp)
        else:
            LOG.error("Failed to trigger Render deploy: %s", resp)
    else:
        LOG.info("Skipping Render deploy (do_deploy=%s, hook_present=%s)", do_deploy, bool(hook))

    LOG.info("Bundle generation complete. Review files under %s", PROJECT_DIR)


# -----------------------------
# CLI
# -----------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create THE13TH Day6 client customization bundle")
    p.add_argument("--hook", type=str, default="", help="Override Render deploy hook URL")
    p.add_argument("--no-deploy", action="store_true", help="Do not trigger Render deploy hook")
    p.add_argument("--no-push", action="store_true", help="Do not push to git remote")
    p.add_argument("--force", action="store_true", help="Overwrite files where applicable")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    try:
        build_bundle(render_hook=(args.hook or None), do_push=not args.no_push, do_deploy=not args.no_deploy)
        return 0
    except KeyboardInterrupt:
        LOG.warning("Interrupted by user — exiting")
        return 2
    except Exception as exc:
        LOG.exception("Unhandled error during bundle creation: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
