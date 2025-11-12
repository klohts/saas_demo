#!/usr/bin/env python3
"""
setup_frontend_serving.py

- Builds React frontend (frontend/)
- Copies frontend/dist -> static/
- Starts FastAPI on APP_PORT (default 8012)

This version checks local `node` version and exits with actionable instructions
if the installed Node is incompatible with modern Vite ESM-only plugins.
"""
from pathlib import Path
import os
import shutil
import subprocess
import logging
import re
import sys
from typing import Tuple

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# ---------------------- Config ---------------------- #
ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"
STATIC_DIR = ROOT_DIR / "static"
INDEX_HTML = STATIC_DIR / "index.html"

PORT = int(os.getenv("APP_PORT", "8012"))
APP_NAME = "THE13TH Frontend Server"

# ---------------------- Logging ---------------------- #
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(APP_NAME)

# ---------------------- Node version helpers ---------------------- #
MIN_ALLOW_VERSIONS = [("20", "19", "0"), ("22", "12", "0")]
NODE_VERSION_PATTERN = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")

def parse_node_version(version_str: str) -> Tuple[int,int,int]:
    m = NODE_VERSION_PATTERN.search(version_str.strip())
    if not m:
        raise ValueError(f"Cannot parse node version from: {version_str!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3))

def node_is_compatible() -> Tuple[bool,str]:
    """Return (is_compatible, version_string)."""
    try:
        proc = subprocess.run(["node", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        ver_raw = proc.stdout.strip()
        major, minor, patch = parse_node_version(ver_raw)
        # Accept >=20.19.0 OR >=22.12.0 (as plugin requires >=20.19.0 or >=22.12.0)
        if (major > 20) or (major == 20 and (minor > 19 or (minor == 19 and patch >= 0))) or (major >= 22 and (minor >= 12)):
            return True, ver_raw
        # allow 21.x as well (21 >20)
        if major == 21:
            return True, ver_raw
        return False, ver_raw
    except FileNotFoundError:
        return False, "node not found"
    except subprocess.CalledProcessError:
        return False, "node --version failed"
    except Exception as e:
        logger.exception("Failed to check node version")
        return False, f"unknown: {e}"

# ---------------------- Shell helper ---------------------- #
def run_command(cmd: str, cwd: Path) -> None:
    logger.info("Running: %s (cwd=%s)", cmd, cwd)
    try:
        subprocess.run(cmd, shell=True, check=True, cwd=cwd)
    except subprocess.CalledProcessError as exc:
        logger.error("Command failed: %s", exc)
        raise

# ---------------------- Build helpers ---------------------- #
def clean_and_copy_dist() -> None:
    if not DIST_DIR.exists():
        raise FileNotFoundError(f"Missing React build directory: {DIST_DIR}")
    if STATIC_DIR.exists():
        shutil.rmtree(STATIC_DIR)
    shutil.copytree(DIST_DIR, STATIC_DIR)
    logger.info("Copied React /dist -> FastAPI /static")

def build_frontend() -> None:
    if not (FRONTEND_DIR / "package.json").exists():
        raise FileNotFoundError("Missing package.json in frontend/ — cannot build frontend.")
    logger.info("Building React frontend (npm install && npm run build)")
    # install + build
    run_command("npm install --no-audit --no-fund", FRONTEND_DIR)
    run_command("npm run build", FRONTEND_DIR)
    clean_and_copy_dist()

# ---------------------- FastAPI app ---------------------- #
def create_app() -> FastAPI:
    app = FastAPI(title=APP_NAME)
    if not STATIC_DIR.exists():
        raise FileNotFoundError("Missing static directory — run build first.")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    @app.middleware("http")
    async def _log(request: Request, call_next):
        logger.info("%s %s", request.method, request.url.path)
        return await call_next(request)

    @app.get("/{full_path:path}", response_class=HTMLResponse)
    async def serve_react_app(full_path: str):
        if full_path.startswith("assets"):
            # Let StaticFiles handle JS/CSS
            return HTMLResponse(status_code=404)
        return FileResponse(INDEX_HTML)

    return app

# ---------------------- Entrypoint ---------------------- #
def main() -> None:
    logger.info("Starting frontend setup and server...")
    ok, ver = node_is_compatible()
    if not ok:
        logger.error("Incompatible Node.js detected: %s", ver)
        logger.error("Vite + some plugins require Node >= 20.19.0 (or >=22.12.0).")
        logger.error("Options to fix:")
        logger.error("  1) Install a compatible Node with nvm (recommended):")
        logger.error("     curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash")
        logger.error("     # then in a new shell:")
        logger.error("     nvm install 20.19.0")
        logger.error("     nvm use 20.19.0")
        logger.error("  2) Build inside Docker (no local Node change). See Dockerfile and docker-compose in the project root.")
        logger.error("  3) If you already installed a newer node with nvm, ensure your shell is using it (nvm use 20.19.0).")
        sys.exit(2)

    try:
        build_frontend()
    except Exception as exc:
        logger.exception("Frontend build failed: %s", exc)
        logger.error("If your Node is compatible, try running the build manually in %s to see full errors.", FRONTEND_DIR)
        raise

    app = create_app()
    logger.info("Frontend ready — serving on http://0.0.0.0:%d", PORT)
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")

if __name__ == "__main__":
    main()
