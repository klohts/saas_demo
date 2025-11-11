#!/usr/bin/env python3
"""
merge_frontend_backend.py
Auto-detects FastAPI backend (saas_onboarding) and merges THE13TH React build.
"""
import os
import subprocess
import shutil
import requests
from pathlib import Path

# ────────────────────────────── CONFIG
PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_BUILD = PROJECT_ROOT / "the13th" / "frontend" / "dist"
BACKEND_ROOT = PROJECT_ROOT / "saas_onboarding" / "app"
BACKEND_MAIN = BACKEND_ROOT / "main.py"
STATIC_DIR = BACKEND_ROOT / "static"
TEMPLATES_DIR = BACKEND_ROOT / "templates"
HEALTH_URL = "https://the13th.onrender.com/healthz"

# ────────────────────────────── BUILD FRONTEND IF NEEDED
def ensure_frontend_built():
    if FRONTEND_BUILD.exists():
        print("✅ Frontend build exists.")
        return
    frontend_dir = FRONTEND_BUILD.parent
    print("⚙️  Building THE13TH frontend…")
    subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
    subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True)
    print("✅ Frontend built successfully.")


# ────────────────────────────── MERGE FRONTEND → BACKEND
def merge_frontend():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    print("🔧 Copying built assets to backend static/…")
    # Clear existing static assets
    for item in STATIC_DIR.glob("*"):
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
    # Copy dist build
    for item in FRONTEND_BUILD.iterdir():
        dest = STATIC_DIR / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
    print("✅ Static assets updated.")


# ────────────────────────────── PATCH main.py TO SERVE REACT BUILD
def patch_main_py():
    if not BACKEND_MAIN.exists():
        raise FileNotFoundError(f"{BACKEND_MAIN} not found.")

    code = BACKEND_MAIN.read_text()

    if "serve_react_frontend" in code:
        print("ℹ️  main.py already patched for frontend serving.")
        return

    react_serve_snippet = """
# --- Serve THE13TH React frontend ---
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_react_frontend(full_path: str):
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "ok", "note": "Frontend build not found"}
"""

    if "app = FastAPI" in code:
        patched = code.replace("app = FastAPI", f"app = FastAPI{react_serve_snippet}")
        BACKEND_MAIN.write_text(patched)
        print("✅ Patched backend main.py to serve React build.")
    else:
        print("⚠️  Could not find FastAPI init; skipping patch.")


# ────────────────────────────── DEPLOY TO RENDER
def trigger_render_deploy():
    deploy_url = "https://api.render.com/deploy/srv-d475kper433s738vdmr0?key=AQ4JOubHX1g"
    print("🚀 Triggering Render deploy…")
    try:
        res = requests.post(deploy_url)
        print(f"Render response: {res.status_code} {res.text}")
    except Exception as e:
        print(f"⚠️  Failed to trigger Render deploy: {e}")


# ────────────────────────────── VERIFY HEALTH
def verify_health():
    print("🩺 Checking /healthz endpoint…")
    try:
        res = requests.get(HEALTH_URL, timeout=15)
        if res.status_code == 200 and "ok" in res.text.lower():
            print("✅ Health check passed.")
        else:
            print(f"⚠️  Unexpected response: {res.status_code} {res.text}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")


# ────────────────────────────── MAIN FLOW
if __name__ == "__main__":
    print("🔧 Merging THE13TH frontend and backend (shared backend mode)…")
    ensure_frontend_built()
    merge_frontend()
    patch_main_py()
    trigger_render_deploy()
    verify_health()
    print("✅ Merge & deploy process complete.")
