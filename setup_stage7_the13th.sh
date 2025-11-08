#!/bin/bash
# ============================================================
# 🧩 THE13TH Stage 7 Setup Script (v4.6.0)
# ------------------------------------------------------------
# Creates all Stage 7 files & directories for THE13TH SaaS app.
# Author: Ken | Project: THE13TH | Date: $(date +'%Y-%m-%d')
# ============================================================

PROJECT_DIR="/home/hp/AIAutomationProjects/saas_demo"
CONFIG_DIR="$PROJECT_DIR/config"
DATA_DIR="$PROJECT_DIR/data"
STATIC_DIR="$PROJECT_DIR/static"

echo "📁 Setting up THE13TH Stage 7 in: $PROJECT_DIR"
mkdir -p "$CONFIG_DIR" "$DATA_DIR" "$STATIC_DIR"

# --- main.py ---
cat > "$PROJECT_DIR/main.py" <<'PYCODE'
import os
import sqlite3
import logging
from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
from client_manager import ClientManager
import json

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_ROOT, "data", "clients.db")
PLANS_PATH = os.path.join(APP_ROOT, "config", "plans.json")
ADMIN_KEY = os.environ.get("ADMIN_KEY", "the13th-admin")

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="THE13TH — Client Module v4.6.0")

app.mount("/static", StaticFiles(directory=os.path.join(APP_ROOT, "static")), name="static")

with open(PLANS_PATH, "r") as f:
    PLANS = json.load(f)

cm = ClientManager(DB_PATH)
cm.init_db()

class UsageMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/static") or path.startswith("/docs") or path.startswith("/admin"):
            return await call_next(request)

        if path.startswith("/api/admin"):
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if not api_key:
            if path.startswith("/api") or path.startswith("/billing"):
                return JSONResponse({"detail": "X-API-Key header required."}, status_code=401)
            return await call_next(request)

        client = cm.get_client_by_api(api_key)
        if not client:
            return JSONResponse({"detail": "Invalid API key."}, status_code=401)

        plan = client.get("plan")
        quota_limit = client.get("quota_limit", 0)
        quota_used = client.get("quota_used", 0)

        if quota_limit is not None and quota_limit != -1 and quota_used >= quota_limit:
            return JSONResponse({"detail": "Quota exceeded."}, status_code=429)

        cm.increment_usage(api_key, 1)
        return await call_next(request)

app.add_middleware(UsageMiddleware)

@app.get("/", response_class=HTMLResponse)
async def home():
    return "<h3>THE13TH — API Platform (Stage 7)</h3><p>See <a href='/admin'>Admin</a></p>"

def check_admin(key: str = Header(None, alias="X-ADMIN-KEY")):
    if key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")

@app.get("/admin", response_class=HTMLResponse)
def admin_ui(key: str = Header(None, alias="X-ADMIN-KEY")):
    check_admin(key)
    with open(os.path.join(APP_ROOT, "static", "admin.html"), "r") as f:
        return HTMLResponse(f.read())

@app.post("/api/admin/clients")
def create_client(payload: dict, key: str = Header(None, alias="X-ADMIN-KEY")):
    check_admin(key)
    name = payload.get("name")
    plan = payload.get("plan", "Free")
    if plan not in PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan")
    client = cm.create_client(name, plan)
    return client

@app.get("/api/admin/clients")
def list_clients(key: str = Header(None, alias="X-ADMIN-KEY")):
    check_admin(key)
    return {"clients": cm.list_clients()}

@app.get("/billing/status")
def billing_status(client: str = None, api_key: str = None):
    if not client and not api_key:
        raise HTTPException(status_code=400, detail="client or api_key required")
    if api_key:
        c = cm.get_client_by_api(api_key)
    else:
        c = cm.get_client_by_name(client)
    if not c:
        raise HTTPException(status_code=404, detail="client not found")
    return {
        "client": c.get("name"),
        "plan": c.get("plan"),
        "quota_limit": c.get("quota_limit"),
        "quota_used": c.get("quota_used")
    }

@app.get("/api/plan")
def get_plans():
    return PLANS

@app.get("/api/hello")
def hello(key: str = Header(None, alias="X-API-Key")):
    client = cm.get_client_by_api(key)
    return {"message": f"hello {client.get('name')}", "plan": client.get('plan')}
PYCODE

# --- client_manager.py ---
cat > "$PROJECT_DIR/client_manager.py" <<'PYCODE'
import sqlite3
import os
import secrets
from datetime import datetime

class ClientManager:
    def __init__(self, db_path="./data/clients.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            api_key TEXT UNIQUE,
            plan TEXT,
            quota_limit INTEGER,
            quota_used INTEGER DEFAULT 0,
            created_at TEXT
        )
        """)
        conn.commit()
        conn.close()

    def generate_api_key(self):
        return secrets.token_urlsafe(24)

    def create_client(self, name, plan, quota_limit=None):
        api_key = self.generate_api_key()
        created_at = datetime.utcnow().isoformat()
        if quota_limit is None:
            defaults = {"Free": 50, "Pro": 1000, "Enterprise": -1}
            quota_limit = defaults.get(plan, 50)
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO clients (name, api_key, plan, quota_limit, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, api_key, plan, quota_limit, created_at)
        )
        conn.commit()
        client_id = cur.lastrowid
        conn.close()
        return self.get_client_by_id(client_id)

    def get_client_by_id(self, client_id):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT id, name, api_key, plan, quota_limit, quota_used, created_at FROM clients WHERE id = ?", (client_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        keys = ["id","name","api_key","plan","quota_limit","quota_used","created_at"]
        return dict(zip(keys, row))

    def get_client_by_api(self, api_key):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT id, name, api_key, plan, quota_limit, quota_used, created_at FROM clients WHERE api_key = ?", (api_key,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        keys = ["id","name","api_key","plan","quota_limit","quota_used","created_at"]
        return dict(zip(keys, row))

    def get_client_by_name(self, name):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT id, name, api_key, plan, quota_limit, quota_used, created_at FROM clients WHERE name = ?", (name,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        keys = ["id","name","api_key","plan","quota_limit","quota_used","created_at"]
        return dict(zip(keys, row))

    def list_clients(self):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT id, name, api_key, plan, quota_limit, quota_used, created_at FROM clients ORDER BY id DESC")
        rows = cur.fetchall()
        conn.close()
        keys = ["id","name","api_key","plan","quota_limit","quota_used","created_at"]
        return [dict(zip(keys, r)) for r in rows]

    def increment_usage(self, api_key, amount=1):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("UPDATE clients SET quota_used = quota_used + ? WHERE api_key = ?", (amount, api_key))
        conn.commit()
        conn.close()
PYCODE

# --- plans.json ---
cat > "$CONFIG_DIR/plans.json" <<'JSON'
{
  "Free": { "quota_limit": 50, "description": "Basic free tier (suitable for testing)" },
  "Pro": { "quota_limit": 1000, "description": "Paid tier with higher limits" },
  "Enterprise": { "quota_limit": -1, "description": "Unlimited (enterprise)" }
}
JSON

# --- admin.html ---
cat > "$STATIC_DIR/admin.html" <<'HTML'
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>THE13TH — Admin</title>
  <style>
    body { font-family: Arial, sans-serif; background:#f5f5f7; color:#222; padding:24px }
    .card { background:white; padding:16px; border-radius:8px; box-shadow:0 4px 14px rgba(0,0,0,0.06); }
    h1 { color:#4b2b85 }
    pre { background:#f0f0f3; padding:12px; border-radius:6px }
  </style>
</head>
<body>
  <div class="card">
    <h1>THE13TH — Admin</h1>
    <p>Use the admin API to create and list clients.</p>
    <h3>Quick curl examples</h3>
    <pre>
# List clients
curl -H "X-ADMIN-KEY: the13th-admin" https://the13th.onrender.com/api/admin/clients

# Create client
curl -X POST -H "Content-Type: application/json" -H "X-ADMIN-KEY: the13th-admin" \
  -d '{"name":"Demo Client","plan":"Free"}' \
  https://the13th.onrender.com/api/admin/clients
    </pre>
  </div>
</body>
</html>
HTML

# --- README_STAGE7.md ---
cat > "$PROJECT_DIR/README_STAGE7.md" <<'MD'
# Stage 7 — Client Module (THE13TH)

## Run locally
(.venv) $ export ADMIN_KEY=the13th-admin
(.venv) $ uvicorn main:app --reload --host 0.0.0.0 --port 8000

## Create client
curl -X POST -H "Content-Type: application/json" -H "X-ADMIN-KEY: the13th-admin" \
  -d '{"name":"Demo Client","plan":"Free"}' http://127.0.0.1:8000/api/admin/clients

## Use client API key
curl -H "X-API-Key: <client_api_key>" http://127.0.0.1:8000/api/hello

## Check billing
curl "http://127.0.0.1:8000/billing/status?api_key=<client_api_key>"
MD


echo "✅ Stage 7 files successfully created!"
echo "📦 Structure ready under: $PROJECT_DIR"
echo "⚙️  Next: run and test locally, then deploy via ./deploy_the13th.sh"
