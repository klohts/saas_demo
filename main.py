import os, json, logging
from datetime import datetime

from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from utils.telemetry import setup_logger, telemetry_middleware

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

# Demo mode flag
DEMO_MODE = os.environ.get("DEMO_MODE", "1") == "1"

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

# Setup telemetry
setup_logger()
telemetry_middleware(app)

# DB init
cm = ClientManager(DB_PATH)
cm.init_db()

# ───────── Middleware ─────────

# ───────── Public Routes ─────────
@app.get("/", response_class=HTMLResponse)
async def home():
    with open(os.path.join(APP_ROOT, "static", "index.html")) as f:
        return HTMLResponse(f.read())


@app.get("/docs13", response_class=HTMLResponse)
@app.get("/docs13", response_class=HTMLResponse)

async def docs13():

    content = f"""

    <html><head><title>{THEME["name"]} — Docs</title>

    <link rel=stylesheet href=/static/the13th.css></head>

    <body class=page>

      <div class=demo-banner>⚙️ DEMO MODE ACTIVE</div>

      <h1>{THEME["name"]} API Quick-Start</h1>

      <p class=tag>{THEME["tagline"]}</p>

      <section class=card>

        <h3>Authentication</h3>

        <code>Header: X-API-Key: &lt;client_api_key&gt;</code>

      </section>

      <section class=card>

        <h3>Endpoints</h3>

        <ul>

          <li><b>GET</b> /api/plan — Available Plans</li>

          <li><b>GET</b> /billing/status — Client quota status</li>

          <li><b>GET</b> /api/hello — Example protected route</li>

        </ul>

      </section>

      <footer><a href=/>← Back to Home</a></footer>

    </body></html>"""

    return HTMLResponse(content)


@app.get("/api/plan")
def get_plans():
    return PLANS

# ───────── Protected Routes ─────────

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

@app.get("/api/hello")
def hello(key: str = Header(None, alias="X-API-Key")):
    """Returns client info and confirms demo mode."""
    demo_path = os.path.join(APP_ROOT, "data", "demo_api_key.txt")
    if DEMO_MODE and not key and os.path.exists(demo_path):
        try:
            key = open(demo_path).read().strip()
        except Exception as e:
            logging.error(f"❌ Could not read demo key: {e}")
    if not key:
        raise HTTPException(status_code=401, detail="X-API-Key header required.")
    c = cm.get_client_by_api(key)
    if not c:
        raise HTTPException(status_code=401, detail="Invalid or missing demo key.")
    return {
        "message": f"hello {c['name']}",
        "plan": c['plan'],
        "demo_mode": DEMO_MODE
    }
# ============================================================
# 🔧 Rebuilt UsageMiddleware (Stage 9.4)
# ============================================================
from starlette.middleware.base import BaseHTTPMiddleware
class UsageMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        # Explicit exclusions: anything public, admin, docs, or demo
        excluded_paths = [
            "/",
            "/docs",
            "/docs13",
            "/static",
            "/admin",
            "/api/admin",
            "/api/plan"
        ]
        if any(path.startswith(p) for p in excluded_paths):
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

# --- Demo client bootstrap (safe persistent storage) ---

# ============================================================
# 🧠 Demo Client Initialization (fixed scope + safe persistence)
# ============================================================

def ensure_demo_client():
    """Ensures a demo client exists and persists its API key safely."""
    clients = cm.list_clients()
    demo_dir = os.path.join(APP_ROOT, "data")
    demo_path = os.path.join(demo_dir, "demo_api_key.txt")

    os.makedirs(demo_dir, exist_ok=True)
    try:
        if not clients:
            logging.info("🧩 Creating demo client (fresh instance)...")
            demo = cm.create_client("Demo Client", "Free")
            with open(demo_path, "w") as f:
                f.write(demo["api_key"])
            logging.info(f"✅ Demo client created with API key: {demo['api_key']}")
        elif not os.path.exists(demo_path):
            demo = clients[0]
            with open(demo_path, "w") as f:
                f.write(demo["api_key"])
            logging.info(f"♻️ Restored demo key from DB: {demo['api_key']}")
        else:
            logging.info("🟣 Demo client already exists; skipping creation.")
    except Exception as e:
        logging.error(f"❌ Failed to initialize demo client: {e}")

if DEMO_MODE:
    ensure_demo_client()

# ============================================================
# 🔑 /api/hello — demo key fallback route (fixed indent)
# ============================================================
@app.get("/api/hello")
def hello(key: str = Header(None, alias="X-API-Key")):
    """Returns client info and confirms demo mode."""
    demo_path = os.path.join(APP_ROOT, "data", "demo_api_key.txt")
    if DEMO_MODE and not key and os.path.exists(demo_path):
        try:
            key = open(demo_path).read().strip()
        except Exception as e:
            logging.error(f"❌ Could not read demo key: {e}")
    if not key:
        raise HTTPException(status_code=401, detail="X-API-Key header required.")
    c = cm.get_client_by_api(key)
    if not c:
        raise HTTPException(status_code=401, detail="Invalid or missing demo key.")
    return {"message": f"hello {c['name']}", "plan": c['plan'], "demo_mode": DEMO_MODE}
