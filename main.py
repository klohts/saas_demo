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
            path.startswith("/api/plan"), path.startswith("/api/admin"),
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
    if DEMO_MODE and not key:
        key_path = os.path.join(APP_ROOT, "tmp_demo_api_key.txt")
        if os.path.exists(key_path):
            key = open(key_path).read().strip()
    c = cm.get_client_by_api(key)
    return {"message": f"hello {c['name']}", "plan": c['plan'], "demo_mode": DEMO_MODE}
