import os, json, logging
from datetime import datetime

from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from utils.patch_adminauth_fix import register_admin_routes
from starlette.middleware.base import BaseHTTPMiddleware
from utils.telemetry import setup_logger, telemetry_middleware, parse_today_metrics

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
LOG_DIR = os.path.join(APP_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, "app.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ],
)


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


@app.get("/api/metrics")
def metrics():
    """Return basic operational metrics for today."""
    return parse_today_metrics()



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

# === Stage 13: Magic Link Client Portal ===
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from utils.auth_magic import init_db, create_magic_link, validate_token
from utils.telemetry import parse_today_metrics

templates = Jinja2Templates(directory="templates")
init_db()

@app.get("/client/signup", response_class=HTMLResponse)
def client_signup():
    return templates.TemplateResponse("client_signup.html", {"request": {}})

@app.get("/api/magic-link")
def magic_link(email: str):
    link = create_magic_link(email)
    return {"email": email, "magic_link": link}

@app.get("/client/login", response_class=HTMLResponse)
def client_login(token: str):
    email = validate_token(token)
    if not email:
        return HTMLResponse("<h2>Invalid or expired link.</h2>", status_code=401)
    response = RedirectResponse(url="/client/dashboard")
    response.set_cookie(key="session_user", value=email, max_age=3600)
    return response

@app.get("/client/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    email = request.cookies.get("session_user")
    if not email:
        return RedirectResponse(url="/client/signup")
    metrics = parse_today_metrics()
    return templates.TemplateResponse("client_dashboard.html",
        {"request": request, "email": email, "metrics": metrics})

# === Stage 13.3: Email Log Viewer ===
@app.get("/admin/email-log", response_class=HTMLResponse)
def view_email_log(request: Request):
    from pathlib import Path
    log_path = Path("logs/email_delivery.log")
    if not log_path.exists():
        content = "No log entries yet."
    else:
        content = log_path.read_text()[-5000:]  # last 5k chars
    return templates.TemplateResponse("email_log.html",
        {"request": request, "log_content": content})

# === Stage 13.4: Admin Overview Dashboard ===
@app.get("/admin/overview", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    from utils.telemetry import parse_today_metrics
    from pathlib import Path
    import json, datetime

    metrics = parse_today_metrics()
    log_path = Path("logs/email_delivery.log")
    log_text = log_path.read_text()[-3000:] if log_path.exists() else "No emails logged yet."

    sent = failed = 0
    if log_path.exists():
        for line in log_text.splitlines():
            if "SENT" in line: sent += 1
            elif "FAILED" in line: failed += 1
    email_stats = {"sent": sent, "failed": failed}

    # Generate dummy hourly request data for chart
    now = datetime.datetime.utcnow()
    hours = [(now - datetime.timedelta(hours=i)).strftime("%H:%M") for i in range(12)][::-1]
    data = [max(0, metrics["requests_today"] // 12 + i % 3) for i in range(12)]

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "metrics": metrics,
        "email_stats": email_stats,
        "chart_labels": json.dumps(hours),
        "chart_data": json.dumps(data),
        "email_log": log_text
    })

from fastapi import Form
from fastapi.responses import RedirectResponse

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "th13_superpass")
DEMO_MODE = True

@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})

@app.post("/admin/login", response_class=RedirectResponse)
def admin_login_submit(request: Request, password: str = Form(...)):
    if password.strip() == ADMIN_PASSWORD:
        response = RedirectResponse(url="/admin/tools", status_code=302)
        response.set_cookie("auth", "1", httponly=True)
        return response
    return HTMLResponse("<h3>❌ Invalid password</h3><a href='/admin/login'>Try again</a>", status_code=403)

def require_admin_auth(request: Request):
    if request.cookies.get("auth") != "1":
        raise HTTPException(status_code=403, detail="Unauthorized")

@app.get("/admin/tools", response_class=HTMLResponse)
def admin_tools(request: Request):
    require_admin_auth(request)
    return templates.TemplateResponse("admin_tools.html", {"request": request})

@app.post("/admin/reset-logs")
def reset_logs(request: Request):
    require_admin_auth(request)
    for f in Path("logs").glob("*.log"):
        f.write_text("")
    return RedirectResponse("/admin/tools", status_code=302)

@app.post("/admin/filter-emails")
def filter_failed_emails(request: Request):
    require_admin_auth(request)
    log_path = Path("logs/email_delivery.log")
    if log_path.exists():
        failed_lines = [line for line in log_path.read_text().splitlines() if "FAILED" in line]
        log_path.write_text("\n".join(failed_lines))
    return RedirectResponse("/admin/tools", status_code=302)

@app.post("/admin/toggle-demo")
def toggle_demo(request: Request):
    require_admin_auth(request)
    global DEMO_MODE
    DEMO_MODE = not DEMO_MODE
    status = "activated" if DEMO_MODE else "deactivated"
    return HTMLResponse(f"<h3>🟣 Demo mode {status}.</h3><a href='/admin/tools'>Back</a>")

register_admin_routes(app, templates)
