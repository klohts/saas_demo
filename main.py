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
