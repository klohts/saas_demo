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
