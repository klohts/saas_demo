import os, json, logging
from datetime import datetime

from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from dotenv import load_dotenv
from client_manager import ClientManager

# Load environment variables
load_dotenv()

# Paths
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_ROOT, "data", "clients.db")
PLANS_PATH = os.path.join(APP_ROOT, "config", "plans.json")
THEME_PATH = os.path.join(APP_ROOT, "config", "theme.json")

# Keys
ADMIN_KEY = os.environ.get("ADMIN_KEY", "the13th-admin")
MASTER_API_KEY = os.environ.get("API_KEY")  # Optional global key

# Load configs
with open(THEME_PATH) as f:
    THEME = json.load(f)
with open(PLANS_PATH) as f:
    PLANS = json.load(f)

# Logging
logging.basicConfig(level=logging.INFO)

# App
app = FastAPI(title=f"{THEME['name']} — v4.7.0")
app.mount("/static", StaticFiles(directory=os.path.join(APP_ROOT, "static")), name="static")

# DB init
cm = ClientManager(DB_PATH)
cm.init_db()

# ───────── Middleware ─────────
class UsageMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Public routes bypass
        if any([
            path.startswith("/static"),
            path.startswith("/docs"),
            path.startswith("/admin"),
            path.startswith("/api/plan"),
            path.startswith("/docs13"),
            path == "/"
        ]):
            return await call_next(request)

        api_key = request.headers.get("X-API-Key") or request.headers.get("X-MASTER-API-Key")
        if not api_key:
            return JSONResponse({"detail": "X-API-Key header required."}, status_code=401)

        # Allow master key bypass
        if MASTER_API_KEY and api_key == MASTER_API_KEY:
            return await call_next(request)

        # Validate client key
        client = cm.get_client_by_api(api_key)
        if not client:
            return JSONResponse({"detail": "Invalid API key."}, status_code=401)

        # Quota check
        if client["quota_limit"] != -1 and client["quota_used"] >= client["quota_limit"]:
            return JSONResponse({"detail": "Quota exceeded."}, status_code=429)

        cm.increment_usage(api_key, 1)
        return await call_next(request)

app.add_middleware(UsageMiddleware)

# ───────── Public Routes ─────────
@app.get("/", response_class=HTMLResponse)
async def home():
    with open(os.path.join(APP_ROOT, "static", "index.html")) as f:
        return HTMLResponse(f.read())


@app.get("/docs13", response_class=HTMLResponse)
async def docs13():
    html = f"""
    <html><head><title>{THEME['name']} — Docs</title>
    <link rel='stylesheet' href='/static/the13th.css'></head>
    <body class='page'>
      <h1 id="brand">{THEME['name']}</h1>
      <p class='tag'>{THEME['tagline']}</p>
      <section class='card'>
        <h3>Authentication</h3>
        <code>Header: X-API-Key: &lt;client_api_key&gt;</code><br/>
        <code>Header: X-MASTER-API-Key: &lt;master_key_optional&gt;</code>
      </section>
      <section class='card'>
        <h3>Endpoints</h3>
        <ul>
          <li><b>GET</b> /api/plan</li>
          <li><b>GET</b> /billing/status</li>
          <li><b>GET</b> /api/hello</li>
        </ul>
      </section>
      <footer><a href='/'>← Back</a></footer>
    </body></html>
    """
    return HTMLResponse(html)


@app.get("/api/plan")
def get_plans():
    return PLANS

# ───────── Protected Routes ─────────
@app.get("/api/hello")
def hello(api_key: str = Header(None, alias="X-API-Key")):
    client = cm.get_client_by_api(api_key)
    if not client:
        raise HTTPException(401, "Invalid API key")
    return {"message": f"hello {client['name']}", "plan": client["plan"]}


@app.get("/billing/status")
def billing_status(api_key: str = Header(None, alias="X-API-Key")):
    client = cm.get_client_by_api(api_key)
    if not client:
        raise HTTPException(404, "client not found")
    return {
        "client": client["name"],
        "plan": client["plan"],
        "quota": client["quota_limit"],
        "used": client["quota_used"],
        "remaining": max(0, client["quota_limit"] - client["quota_used"])
        if client["quota_limit"] != -1 else "∞"
    }

# ───────── Admin Route ─────────
@app.get("/api/admin/clients")
def list_clients(key: str = Header(None, alias="X-ADMIN-KEY")):
    if key != ADMIN_KEY:
        raise HTTPException(403, "Invalid admin key")
    return {"clients": cm.list_clients()}
