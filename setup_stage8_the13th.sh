#!/bin/bash
# ============================================================
# ✨ THE13TH Stage 8 Setup Script (v4.7.0)
# ------------------------------------------------------------
# Builds the Branding & Demo Layer for THE13TH SaaS Platform.
# Author: Ken | Project: THE13TH | Date: $(date +'%Y-%m-%d')
# ============================================================

PROJECT_DIR="/home/hp/AIAutomationProjects/saas_demo"
STATIC_DIR="$PROJECT_DIR/static"
CONFIG_DIR="$PROJECT_DIR/config"
ASSETS_DIR="$STATIC_DIR/assets"

echo "📁 Setting up THE13TH Stage 8 in: $PROJECT_DIR"
mkdir -p "$STATIC_DIR" "$ASSETS_DIR" "$CONFIG_DIR"

# --- main.py (v4.7.0) ---
cat > "$PROJECT_DIR/main.py" <<'PYCODE'
import os, json, logging, sqlite3
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
from client_manager import ClientManager

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_ROOT, "data", "clients.db")
PLANS_PATH = os.path.join(APP_ROOT, "config", "plans.json")
THEME_PATH = os.path.join(APP_ROOT, "config", "theme.json")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "the13th-admin")

with open(THEME_PATH) as f:
    THEME = json.load(f)
with open(PLANS_PATH) as f:
    PLANS = json.load(f)

logging.basicConfig(level=logging.INFO)
app = FastAPI(title=f"{THEME['name']} — v4.7.0")

app.mount("/static", StaticFiles(directory=os.path.join(APP_ROOT, "static")), name="static")
cm = ClientManager(DB_PATH)
cm.init_db()

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
    with open(os.path.join(APP_ROOT, "static", "index.html")) as f:
        return HTMLResponse(f.read())

@app.get("/docs13", response_class=HTMLResponse)
async def docs13():
    content = f"""
    <html><head><title>{THEME['name']} — Docs</title>
    <link rel='stylesheet' href='/static/the13th.css'></head>
    <body class='page'>
      <h1>{THEME['name']} API Quick-Start</h1>
      <p class='tag'>{THEME['tagline']}</p>
      <section class='card'>
        <h3>Authentication</h3>
        <code>Header: X-API-Key: &lt;client_api_key&gt;</code>
      </section>
      <section class='card'>
        <h3>Endpoints</h3>
        <ul>
          <li><b>GET</b> /api/plan — Available Plans</li>
          <li><b>GET</b> /billing/status — Client quota status</li>
          <li><b>GET</b> /api/hello — Example protected route</li>
        </ul>
      </section>
      <footer><a href='/'>← Back to Home</a></footer>
    </body></html>"""
    return HTMLResponse(content)

@app.get("/api/plan")
def get_plans(): return PLANS

@app.get("/api/hello")
def hello(key: str = Header(None, alias="X-API-Key")):
    client = cm.get_client_by_api(key)
    return {"message": f"hello {client.get('name')}", "plan": client.get('plan')}

@app.get("/billing/status")
def billing_status(api_key: str):
    c = cm.get_client_by_api(api_key)
    if not c: raise HTTPException(404, "client not found")
    return {"client": c["name"], "plan": c["plan"], "quota": c["quota_limit"], "used": c["quota_used"]}

@app.get("/api/admin/clients")
def list_clients(key: str = Header(None, alias="X-ADMIN-KEY")):
    if key != ADMIN_KEY: raise HTTPException(403, "Invalid admin key")
    return {"clients": cm.list_clients()}
PYCODE

# --- index.html ---
cat > "$STATIC_DIR/index.html" <<'HTML'
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>THE13TH — Where Automation Meets Intuition</title>
  <link rel="stylesheet" href="/static/the13th.css">
</head>
<body class="page">
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

# --- admin.html ---
cat > "$STATIC_DIR/admin.html" <<'HTML'
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>THE13TH — Admin Dashboard</title>
  <link rel="stylesheet" href="/static/the13th.css">
</head>
<body class="page">
  <h1>THE13TH — Admin Dashboard</h1>
  <p class="tag">Manage clients and usage plans.</p>
  <section class="card">
    <h3>List Clients</h3>
    <code>curl -H "X-ADMIN-KEY: the13th-admin" https://the13th.onrender.com/api/admin/clients</code>
  </section>
  <section class="card">
    <h3>Create Client</h3>
    <code>curl -X POST -H "Content-Type: application/json" -H "X-ADMIN-KEY: the13th-admin" \
      -d '{"name":"Demo Client","plan":"Free"}' https://the13th.onrender.com/api/admin/clients</code>
  </section>
  <footer><a href="/">← Back Home</a></footer>
</body>
</html>
HTML

# --- the13th.css ---
cat > "$STATIC_DIR/the13th.css" <<'CSS'
body.page { background:#1E1E1E; color:#ECECEC; font-family:'Inter',sans-serif; text-align:center; padding:40px; }
.logo { width:80px; margin-bottom:16px; filter:drop-shadow(0 0 8px #9D5FFB); }
h1 { font-size:3em; color:#9D5FFB; margin-bottom:0; }
.tag { color:#b3b3b3; margin:8px 0 32px; }
.card { background:#2A2A2A; margin:16px auto; padding:20px; max-width:600px; border-radius:16px;
        box-shadow:0 0 15px rgba(157,95,251,0.25); }
.button { display:inline-block; margin:8px; padding:12px 24px; border-radius:8px; text-decoration:none;
          background:#9D5FFB; color:#fff; transition:0.3s; }
.button:hover { background:#b076ff; }
.button.ghost { background:transparent; border:1px solid #9D5FFB; color:#9D5FFB; }
footer { margin-top:40px; color:#777; }
CSS

# --- THE13TH.svg ---
cat > "$ASSETS_DIR/THE13TH.svg" <<'SVG'
<svg width="120" height="120" xmlns="http://www.w3.org/2000/svg">
  <circle cx="60" cy="60" r="55" stroke="#9D5FFB" stroke-width="2" fill="none"/>
  <text x="50%" y="55%" text-anchor="middle" fill="#9D5FFB" font-size="22" font-family="monospace">13</text>
</svg>
SVG

# --- theme.json ---
cat > "$CONFIG_DIR/theme.json" <<'JSON'
{
  "name": "THE13TH",
  "tagline": "The unseen layer of intelligence — where automation meets intuition.",
  "primary_color": "#9D5FFB",
  "background_color": "#1E1E1E",
  "text_color": "#ECECEC"
}
JSON

# --- README_STAGE8.md ---
cat > "$PROJECT_DIR/README_STAGE8.md" <<'MD'
# Stage 8 — Branding & Demo Layer (THE13TH)

## Run locally
(.venv)$ uvicorn main:app --reload --host 0.0.0.0 --port 8000

## Demo pages
- Landing: http://127.0.0.1:8000/
- Admin:   http://127.0.0.1:8000/admin
- Docs13:  http://127.0.0.1:8000/docs13

## Deploy
./deploy_the13th.sh
MD

# --- Finish ---
echo "✅ Stage 8 files successfully created!"
echo "📦 Branding & Demo Layer ready under: $PROJECT_DIR"
echo "⚙️  Next: commit & deploy via ./deploy_the13th.sh"
