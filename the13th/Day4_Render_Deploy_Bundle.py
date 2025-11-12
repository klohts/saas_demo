#!/usr/bin/env python3
"""
Day4_Render_Deploy_Bundle.py

Single-script generator and executor for THE13TH Render deployment bundle.
What it does:
- Scaffolds the full repository structure and files (Dockerfile, render.yaml, backend, frontend, deploy script, .env.example, .gitignore)
- Optionally runs frontend build (if Node/npm present)
- Optionally installs Python deps into a virtualenv
- Optionally runs the FastAPI app locally with uvicorn
- Optionally triggers the Render deploy hook (if RENDER_DEPLOY_HOOK env var is set)

Usage:
  python Day4_Render_Deploy_Bundle.py --root /path/to/saas_demo [--build-frontend] [--install-deps] [--run-backend] [--trigger-deploy]

Notes:
- Uses environment variables for secrets (BASIC_AUTH_USER, BASIC_AUTH_PASS, RENDER_DEPLOY_HOOK)
- Creates files exactly where required. Idempotent: existing files will not be overwritten unless --force provided.

Author: Generated for Ken (AI/ML AppsDev) — production-ready scaffolding script.
"""

from __future__ import annotations

import argparse
import os
import sys
import stat
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Optional

# ---- Logging ----
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("day4.bundle")

# ---- File templates ----
DOCKERFILE = r"""
# Multi-stage Dockerfile
# Stage 1: Build frontend with Node 20
FROM node:20 AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/
COPY frontend/src ./src
COPY frontend/index.html ./index.html
RUN npm ci
RUN npm run build

# Stage 2: Production Python runtime with FastAPI
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# system deps for uvicorn, static serving
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# copy backend
COPY backend/requirements.txt ./backend/requirements.txt
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r backend/requirements.txt

# copy backend app
COPY backend/app ./backend/app

# copy built frontend into backend static served folder (auto-copy)
COPY --from=frontend-builder /app/frontend/dist ./backend/app/dist

# create non-root user
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

ENV PORT=8000
EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
"""

RENDER_YAML = r"""
# Render service spec for a Web Service (repository deploy)
services:
  - type: web
    name: the13th
    env: docker
    plan: free
    dockerfilePath: Dockerfile
    healthCheckPath: /api/healthz
    envVars:
      - key: BASIC_AUTH_USER
        fromService: null
      - key: BASIC_AUTH_PASS
        fromService: null
      - key: RENDER_DEPLOY_HOOK
        fromService: null
      - key: APP_ENV
        value: production
"""

GITIGNORE = r"""
__pycache__/
.env
node_modules/
dist/
.vscode/
*.pyc
*.pyo
*.pyd
*.db
"""

ENV_EXAMPLE = r"""
# Copy to .env and fill values before local run
BASIC_AUTH_USER=your_basic_user
BASIC_AUTH_PASS=your_basic_password
RENDER_DEPLOY_HOOK=https://api.render.com/deploy/srv-xxxxxxxxxx?key=SECRET
APP_ENV=development
PORT=8000
"""

REDEPLOY_SH = r"""
#!/usr/bin/env bash
set -euo pipefail

if [ -z "${RENDER_DEPLOY_HOOK:-}" ]; then
  echo "ERROR: RENDER_DEPLOY_HOOK not set. Export it first."
  exit 2
fi

echo "Triggering Render deploy hook..."
curl -sS -X POST "$RENDER_DEPLOY_HOOK" -H "Content-Type: application/json" -d '{}' \
  && echo "Deploy triggered." || { echo "Failed to trigger deploy"; exit 3; }
"""

BACKEND_REQUIREMENTS = r"""
fastapi==0.100.0
uvicorn[standard]==0.22.0
pydantic==2.6.0
python-multipart==0.0.6
"""

BACKEND_INIT = "# package marker\n"

SCHEMAS_PY = r"""
from pydantic import BaseModel, Field
from typing import Optional

class EventPayload(BaseModel):
    source: str = Field(..., min_length=1, description="Source of the event")
    message: str = Field(..., min_length=1)
    metadata: Optional[dict] = None
"""

AUTH_PY = r"""
import os
import base64
from fastapi import Request, HTTPException, status
from typing import Tuple


def _get_basic_credentials() -> Tuple[str, str]:
    user = os.getenv("BASIC_AUTH_USER")
    pwd = os.getenv("BASIC_AUTH_PASS")
    if not user or not pwd:
        return ("", "")
    return (user, pwd)


def require_basic_auth(request: Request):
    expected_user, expected_pass = _get_basic_credentials()
    auth = request.headers.get("Authorization")
    if not expected_user and not expected_pass:
        return True

    if not auth or not auth.startswith("Basic "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized",
                            headers={"WWW-Authenticate": "Basic"})
    try:
        payload = base64.b64decode(auth.split(" ", 1)[1]).decode()
        user, pwd = payload.split(":", 1)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized",
                            headers={"WWW-Authenticate": "Basic"})
    if not (user == expected_user and pwd == expected_pass):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized",
                            headers={"WWW-Authenticate": "Basic"})
    return True
"""

MAIN_PY = r"""
import os
import logging
import time
from typing import Dict
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from .schemas import EventPayload
from .auth import require_basic_auth

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("the13th")

app = FastAPI(title="THE13TH", version="0.1.0")

@app.get("/api/healthz")
def healthz():
    return {"status": "ok", "app": "THE13TH"}

RATE_LIMIT = int(os.getenv("RATE_LIMIT_COUNT", "30"))
RATE_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
_rate_store: Dict[str, Dict[str, int]] = {}


def _rate_check(ip: str):
    now = int(time.time())
    rec = _rate_store.get(ip)
    if not rec:
        _rate_store[ip] = {"count": 1, "start": now}
        return
    start = rec["start"]
    if now - start > RATE_WINDOW:
        _rate_store[ip] = {"count": 1, "start": now}
        return
    if rec["count"] >= RATE_LIMIT:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
    rec["count"] += 1


@app.post("/api/events")
async def create_event(request: Request, payload: EventPayload, authorized: bool = Depends(require_basic_auth)):
    client_ip = request.client.host if request.client else "unknown"
    _rate_check(client_ip)

    try:
        logger.info("Received event: source=%s message=%s", payload.source, payload.message)
        return JSONResponse({"status": "accepted"}, status_code=status.HTTP_202_ACCEPTED)
    except ValidationError as e:
        logger.warning("Validation error: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        logger.exception("Unhandled error in create_event")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error")

# Serve static frontend (built into ./dist)
dist_path = os.path.join(os.path.dirname(__file__), "dist")
if os.path.isdir(dist_path):
    app.mount("/", StaticFiles(directory=dist_path, html=True), name="frontend")
    logger.info("Mounted frontend static files from %s", dist_path)
else:
    logger.warning("No frontend build found at %s — index will redirect to health", dist_path)
    @app.get("/")
    def index_redirect():
        return RedirectResponse(url="/api/healthz")
"""

FRONTEND_PACKAGE_JSON = r"""
{
  "name": "the13th-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build --outDir dist",
    "preview": "vite preview --port 5173"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "vite": "^5.3.0",
    "@vitejs/plugin-react": "^5.1.0"
  }
}
"""

FRONTEND_INDEX_HTML = r"""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>THE13TH Dashboard</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""

FRONTEND_MAIN_JSX = r"""
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

const root = createRoot(document.getElementById("root"));
root.render(<App />);
"""

FRONTEND_APP_JSX = r"""
import React from "react";

export default function App() {
  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: 40 }}>
      <h1 style={{ fontSize: 28, marginBottom: 12 }}>The 13th Intelligence Dashboard</h1>
      <p style={{ maxWidth: 800 }}>
        Welcome — this is the frontend placeholder. When built, these files will be copied into the FastAPI
        runtime image and served at the root URL.
      </p>

      <div style={{ marginTop: 24 }}>
        <a href="/api/healthz" style={{ marginRight: 12 }}>Health</a>
        <a href="/api/events">Events API</a>
      </div>
    </main>
  );
}
"""

# ---- Helpers ----

def write_file(path: Path, content: str, force: bool = False) -> None:
    if path.exists() and not force:
        logger.info("Skipping existing file: %s", path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.info("Wrote: %s", path)


def make_executable(path: Path) -> None:
    st = path.stat().st_mode
    path.chmod(st | stat.S_IEXEC)
    logger.info("Made executable: %s", path)


def run_cmd(cmd: list[str], cwd: Optional[Path] = None) -> None:
    logger.info("Running command: %s (cwd=%s)", " ".join(cmd), cwd)
    subprocess.check_call(cmd, cwd=str(cwd) if cwd else None)


# ---- Main scaffold function ----

def scaffold(root: Path, force: bool = False) -> None:
    logger.info("Scaffolding repo at %s", root)

    # top-level files
    write_file(root / "Dockerfile", DOCKERFILE, force=force)
    write_file(root / "render.yaml", RENDER_YAML, force=force)
    write_file(root / ".env.example", ENV_EXAMPLE, force=force)
    write_file(root / ".gitignore", GITIGNORE, force=force)

    # deploy script
    deploy_dir = root / "deploy"
    write_file(deploy_dir / "redeploy.sh", REDEPLOY_SH, force=force)
    make_executable(deploy_dir / "redeploy.sh")

    # backend
    backend_app = root / "backend" / "app"
    write_file(root / "backend" / "requirements.txt", BACKEND_REQUIREMENTS, force=force)
    write_file(backend_app / "__init__.py", BACKEND_INIT, force=force)
    write_file(backend_app / "schemas.py", SCHEMAS_PY, force=force)
    write_file(backend_app / "auth.py", AUTH_PY, force=force)
    write_file(backend_app / "main.py", MAIN_PY, force=force)

    # frontend
    frontend = root / "frontend"
    write_file(frontend / "package.json", FRONTEND_PACKAGE_JSON, force=force)
    write_file(frontend / "index.html", FRONTEND_INDEX_HTML, force=force)
    write_file(frontend / "src" / "main.jsx", FRONTEND_MAIN_JSX, force=force)
    write_file(frontend / "src" / "App.jsx", FRONTEND_APP_JSX, force=force)

    logger.info("Scaffold complete.")


# ---- Optional operations ----

def build_frontend(root: Path) -> None:
    frontend_dir = root / "frontend"
    if not shutil.which("npm"):
        logger.warning("npm not found in PATH. Skipping frontend build. Install Node/npm to build frontend.")
        return
    # install deps and build
    run_cmd(["npm", "ci"], cwd=frontend_dir)
    run_cmd(["npm", "run", "build"], cwd=frontend_dir)
    logger.info("Frontend build complete.")


def install_python_deps(root: Path) -> None:
    venv_dir = root / ".venv"
    if not venv_dir.exists():
        logger.info("Creating virtualenv at %s", venv_dir)
        run_cmd([sys.executable, "-m", "venv", str(venv_dir)])
    pip = venv_dir / "bin" / "pip"
    if not pip.exists():
        logger.error("pip not found in venv. Something went wrong.")
        return
    run_cmd([str(pip), "install", "-r", str(root / "backend" / "requirements.txt")])
    logger.info("Python deps installed into virtualenv: %s", venv_dir)


def run_backend(root: Path) -> None:
    venv_python = root / ".venv" / "bin" / "python"
    if not venv_python.exists():
        logger.warning("Virtualenv python not found. Attempting to run with system python.")
        venv_python = Path(sys.executable)
    cmd = [str(venv_python), "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", os.getenv("PORT", "8000")]
    logger.info("Starting backend: %s", cmd)
    # Use subprocess.run so the script can forward logs. This will block until process ends.
    subprocess.run(cmd, cwd=str(root))


def trigger_deploy_hook() -> None:
    hook = os.getenv("RENDER_DEPLOY_HOOK")
    if not hook:
        logger.error("RENDER_DEPLOY_HOOK not set in environment. Cannot trigger deploy.")
        return
    run_cmd(["curl", "-sS", "-X", "POST", hook, "-H", "Content-Type: application/json", "-d", "{}"])
    logger.info("Triggered deploy hook.")


# ---- CLI ----

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Create and optionally build/run THE13TH Render deployment bundle.")
    p.add_argument("--root", "-r", type=Path, default=Path.cwd() / "saas_demo", help="Root path to create the project")
    p.add_argument("--force", "-f", action="store_true", help="Overwrite existing files")
    p.add_argument("--build-frontend", action="store_true", help="Run npm ci && npm run build (requires npm)")
    p.add_argument("--install-deps", action="store_true", help="Create venv and install Python deps")
    p.add_argument("--run-backend", action="store_true", help="Run the backend locally with uvicorn (blocks)")
    p.add_argument("--trigger-deploy", action="store_true", help="Trigger Render deploy hook using RENDER_DEPLOY_HOOK env var")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root: Path = args.root.resolve()
    logger.info("Using root: %s", root)

    try:
        scaffold(root, force=args.force)

        if args.build_frontend:
            build_frontend(root)

        if args.install_deps:
            install_python_deps(root)

        if args.trigger_deploy:
            trigger_deploy_hook()

        if args.run_backend:
            run_backend(root)

        logger.info("All requested operations completed.")
    except subprocess.CalledProcessError as e:
        logger.exception("Command failed: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        sys.exit(2)


if __name__ == "__main__":
    main()
