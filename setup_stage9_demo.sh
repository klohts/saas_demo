#!/bin/bash
# ============================================================
# 🚀 THE13TH Stage 9 Setup Script (v4.8.0)
# ------------------------------------------------------------
# Demo Packaging & One-Click Deploy Layer
# Author: Ken | Project: THE13TH | Date: $(date +'%Y-%m-%d')
# ============================================================

PROJECT_DIR="/home/hp/AIAutomationProjects/saas_demo"
STATIC_DIR="$PROJECT_DIR/static"

echo "📦 Setting up THE13TH Stage 9 (Demo Packaging)..."
mkdir -p "$STATIC_DIR"

# --- main.py (v4.8.0) ---
cat > "$PROJECT_DIR/main.py" <<'PYCODE'
import os, json, sqlite3, logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from client_manager import ClientManager

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_ROOT, "data", "clients.db")
PLANS_PATH = os.path.join(APP_ROOT, "config", "plans.json")
THEME_PATH = os.path.join(APP_ROOT, "config", "theme.json")

ADMIN_KEY = os.getenv("ADMIN_KEY", "the13th-admin")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Initialize
logging.basicConfig(level=logging.INFO)
app = FastAPI(title="THE13TH — Demo Edition v4.8.0")

app.mount("/static", StaticFiles(directory=os.path.join(APP_ROOT, "static")), name="static")

with open(PLANS_PATH) as f: PLANS = json.load(f)
with open(THEME_PATH) as f: THEME = json.load(f)
cm = ClientManager(DB_PATH)
cm.init_db()

# --- Demo client bootstrap ---
def ensure_demo_client():
    clients = cm.list_clients()
    if not clients:
        logging.info("🧩 Creating demo client...")
        demo = cm.create_client("Demo Client", "Free")
        with open(os.path.join(APP_ROOT, "tmp_demo_api_key.txt"), "w") as f:
            f.write(demo["api_key"])
        logging.info(f"✅ Demo client created with API key: {demo['api_key']}")

if DEMO_MODE: ensure_demo_client()

# --- Middleware ---
class UsageMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any([
            path.startswith("/static"),
            path.startswith("/docs"),
            path.startswith("/admin"),
            path.startswith("/api/plan"),
            path.startswith("/docs13"),
            path == "/"
        ]):
            return await call_next(request)
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse({"detail": "X-API-Key header required."}, status_code=401)
        client = cm.get_client_by_api(api_key)
        if not client:
            return JSONResponse({"detail": "Invalid API key."}, status_code=401)
        quota_limit, quota_used = client.get("quota_limit", 0), client.get("quota_used", 0)
        if quota_limit != -1 and quota_used >= quota_limit:
            return JSONResponse({"detail": "Quota exceeded."}, status_code=429)
        cm.increment_usage(api_key, 1)
        return await call_next(request)

app.add_middleware(UsageMiddleware)

@app.get("/", response_class=HTMLResponse)
async def home():
    page = open(os.path.join(APP_ROOT, "static", "index.html")).read()
    banner = '<div class="demo-banner">⚙️ DEMO MODE ACTIVE</div>' if DEMO_MODE else ""
    return HTMLResponse(banner + page)

@app.get("/api/plan") 
def get_plans(): return PLANS

@app.get("/api/admin/clients")
def list_clients(key: str = Header(None, alias="X-ADMIN-KEY")):
    if key != ADMIN_KEY: raise HTTPException(403, "Invalid admin key")
    return {"clients": cm.list_clients()}

@app.get("/billing/status")
def billing_status(api_key: str):
    c = cm.get_client_by_api(api_key)
    if not c: raise HTTPException(404, "client not found")
    return {"client": c["name"], "plan": c["plan"], "quota": c["quota_limit"], "used": c["quota_used"]}

@app.get("/api/hello")
def hello(key: str = Header(None, alias="X-API-Key")):
    c = cm.get_client_by_api(key)
    return {"message": f"hello {c['name']}", "plan": c['plan'], "demo_mode": DEMO_MODE}
PYCODE

# --- render-deploy.json ---
cat > "$PROJECT_DIR/render-deploy.json" <<'JSON'
{
  "services": [
    {
      "type": "web_service",
      "env": "python",
      "name": "THE13TH",
      "repo": "https://github.com/klohts/saas_demo",
      "branch": "main",
      "buildCommand": "pip install -r requirements.txt",
      "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
      "envVars": [
        { "key": "DEMO_MODE", "value": "true" },
        { "key": "ADMIN_KEY", "value": "the13th-admin" }
      ]
    }
  ]
}
JSON

# --- index.html update (adds demo banner style) ---
cat > "$STATIC_DIR/index.html" <<'HTML'
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>THE13TH — Demo Edition</title>
  <link rel="stylesheet" href="/static/the13th.css">
</head>
<body class="page">
  <div class="demo-banner">⚙️ DEMO MODE ACTIVE</div>
  <section class="hero">
    <img src="/static/assets/THE13TH.svg" class="logo" alt="THE13TH">
    <h1>THE13TH</h1>
    <p class="tag">The unseen layer of intelligence — where automation meets intuition.</p>
    <div class="cta">
      <a href="/docs13" class="button">API Docs</a>
      <a href="/admin" class="button ghost">Admin</a>
    </div>
  </section>
</body>
</html>
HTML

# --- admin.html update (adds demo banner) ---
cat > "$STATIC_DIR/admin.html" <<'HTML'
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>THE13TH — Admin Dashboard (Demo)</title>
  <link rel="stylesheet" href="/static/the13th.css">
</head>
<body class="page">
  <div class="demo-banner">⚙️ DEMO MODE ACTIVE</div>
  <h1>THE13TH — Admin Dashboard</h1>
  <p class="tag">Manage clients and usage plans.</p>
  <section class="card">
    <h3>List Clients</h3>
    <code>curl -H "X-ADMIN-KEY: the13th-admin" https://the13th.onrender.com/api/admin/clients</code>
  </section>
  <footer><a href="/">← Back Home</a></footer>
</body>
</html>
HTML

# --- README_STAGE9.md ---
cat > "$PROJECT_DIR/README_STAGE9.md" <<'MD'
# Stage 9 — Demo Packaging (THE13TH)

## Run locally
(.venv) $ export DEMO_MODE=true
(.venv) $ uvicorn main:app --reload --host 0.0.0.0 --port 8000

Then open http://127.0.0.1:8000 — you’ll see the DEMO MODE banner.

## One-click Render Deploy
Add this JSON to your repo root:
render-deploy.json

Then visit:
https://render.com/deploy

Paste the repo link and Render will auto-detect settings.

## Demo Client
A "Demo Client" is auto-created on startup when DEMO_MODE=true.
API key is logged in tmp_demo_api_key.txt
MD

# --- Finish ---
echo "✅ Stage 9 (v4.8.0) files created successfully!"
echo "📦 Demo Packaging Layer ready."
echo "🚀 Next: commit & deploy via ./deploy_the13th.sh"
