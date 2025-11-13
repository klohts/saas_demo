"""
THE13TH - Single-file Tenant Dashboard (FastAPI + SQLite + Embedded React)
File: the13th_single_script.py

Purpose:
- Single Python script that implements the backend (FastAPI) with SQLite storage,
  API-key auth, rate limiting, logging, seed data, and two API endpoints:
    - GET /api/tenants
    - GET /api/tenants/{id}
- Serves a simple React + Tailwind-based frontend as a static HTML page at /
  that lists tenants and shows tenant cards (gray/purple theme).

Design decisions made to satisfy Ken's Dev Mode:
- Single file deliverable for rapid MVP deployment.
- Environment variables used for secrets/config; see DEFAULTS below.
- Type hints, structured logging, validation, error handling included.
- In-memory rate limiter for single-instance deployments (fine for Render single instance).
- Uses sqlmodel for ORM and SQLModel/SQLite for DB.

How to run (local dev):
1. Create and activate venv (recommended):
   python -m venv .venv
   source .venv/bin/activate   # mac/linux
   .\.venv\Scripts\activate  # windows (powershell)

2. Install requirements:
   pip install fastapi uvicorn[standard] sqlmodel python-dotenv

3. Set env vars or copy defaults. Minimal example (Linux/mac):
   export DATABASE_URL="sqlite:///./the13th_data/the13th.db"
   export API_KEY="changeme_api_key_here"
   export HOST="0.0.0.0"
   export PORT="8000"

4. Run:
   python the13th_single_script.py

5. Open http://localhost:8000 in your browser.
   The frontend will call the backend with the API key embedded in the served page.

Notes:
- For Render deployment, add this single file to a Python service and set env vars in Render dashboard.
- For multi-instance production, replace rate limiter with Redis-backed solution and do NOT embed API key in client HTML.

"""

from __future__ import annotations

import os
import time
import logging
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, Header, HTTPException, status, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseSettings
from sqlmodel import SQLModel, Field, create_engine, Session, select

# ---------------------------
# Configuration (env-driven)
# ---------------------------

class Settings(BaseSettings):
    database_url: str = os.environ.get("DATABASE_URL", "sqlite:///./data/the13th.db")
    api_key: str = os.environ.get("API_KEY", "changeme_api_key_here")
    host: str = os.environ.get("HOST", "0.0.0.0")
    port: int = int(os.environ.get("PORT", "8000"))
    rate_limit_requests: int = int(os.environ.get("RATE_LIMIT_REQUESTS", "60"))
    rate_limit_window_seconds: int = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))

    class Config:
        env_file = ".env"

settings = Settings()

# ---------------------------
# Logging
# ---------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("the13th.single")

# ---------------------------
# Database (SQLModel + SQLite)
# ---------------------------

# Ensure parent dir exists for sqlite
if settings.database_url.startswith("sqlite"):
    path = settings.database_url.split("///")[-1]
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except Exception:
        # In case dirname is empty (in-memory sqlite) ignore
        pass

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)

class Tenant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    status: str = Field(default="active")  # active | paused | suspended
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity_at: Optional[datetime] = None
    total_events: int = Field(default=0)

# ---------------------------
# DB helpers
# ---------------------------

def init_db() -> None:
    """Create tables if missing."""
    logger.info("Initializing database and creating tables (if needed)")
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine)


def seed_example_tenants() -> None:
    logger.info("Seeding example tenants if DB empty")
    session = get_session()
    try:
        q = session.exec(select(Tenant))
        existing = q.all()
        if existing:
            logger.info("Found %d existing tenants, skipping seed", len(existing))
            return
        now = datetime.utcnow()
        tenants = [
            Tenant(name="Acme Realty", status="active", total_events=124, last_activity_at=now - timedelta(hours=2)),
            Tenant(name="BlueStone Homes", status="paused", total_events=39, last_activity_at=now - timedelta(days=3)),
            Tenant(name="Cornerstone Brokers", status="active", total_events=512, last_activity_at=now - timedelta(minutes=30)),
        ]
        session.add_all(tenants)
        session.commit()
        logger.info("Seeded %d tenants", len(tenants))
    except Exception:
        logger.exception("Failed to seed tenants")
    finally:
        session.close()

# ---------------------------
# Services
# ---------------------------

def list_tenants(limit: int = 50, offset: int = 0, status: Optional[str] = None) -> Tuple[int, List[Tenant]]:
    session = get_session()
    try:
        stmt = select(Tenant)
        if status:
            stmt = stmt.where(Tenant.status == status)
        total = session.exec(select(Tenant)).count()  # may return int
        items = session.exec(stmt.offset(offset).limit(limit)).all()
        # Fallback if count() does not behave as expected
        if not isinstance(total, int):
            total = len(items)
        return total, items
    finally:
        session.close()


def get_tenant(tenant_id: int) -> Optional[Tenant]:
    session = get_session()
    try:
        return session.get(Tenant, tenant_id)
    finally:
        session.close()

# ---------------------------
# Auth
# ---------------------------

async def api_key_auth(x_api_key: Optional[str] = Header(default=None)) -> None:
    if x_api_key is None or x_api_key != settings.api_key:
        logger.warning("Unauthorized request: missing or invalid API key")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

# ---------------------------
# Middleware - simple in-memory rate limiter
# ---------------------------

class SimpleRateLimiter(BaseHTTPMiddleware):
    def __init__(self, app, window_seconds: int = 60, max_requests: int = 60):
        super().__init__(app)
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self._store: Dict[str, Dict[str, float]] = defaultdict(lambda: {"count": 0.0, "reset": 0.0})

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        rec = self._store[ip]
        now = time.time()
        if rec["reset"] < now:
            rec["count"] = 0.0
            rec["reset"] = now + self.window_seconds

        rec["count"] += 1.0
        remaining = int(max(0, self.max_requests - rec["count"]))
        if rec["count"] > self.max_requests:
            logger.warning("Rate limit exceeded for %s", ip)
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(rec["reset"]))
        return response

# ---------------------------
# FastAPI app & routes
# ---------------------------

app = FastAPI(title="THE13TH - Single File Tenant Dashboard", version="1.0")

# CORS — allow local dev origins; Render will need explicit origins in production
app.add_middleware(SimpleRateLimiter, window_seconds=settings.rate_limit_window_seconds, max_requests=settings.rate_limit_requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],  # '*' allowed for convenience in single-file demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup events
@app.on_event("startup")
def _startup():
    try:
        init_db()
        seed_example_tenants()
        logger.info("Startup complete — database initialized and seeded")
    except Exception:
        logger.exception("Startup failed")

# API: list tenants
@app.get("/api/tenants")
def api_list_tenants(limit: int = 50, offset: int = 0, status: Optional[str] = None, _: None = Depends(api_key_auth)) -> JSONResponse:
    try:
        total, items = list_tenants(limit=limit, offset=offset, status=status)
        payload = {
            "total": total,
            "items": [
                {
                    "id": t.id,
                    "name": t.name,
                    "status": t.status,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "last_activity_at": t.last_activity_at.isoformat() if t.last_activity_at else None,
                    "total_events": t.total_events,
                }
                for t in items
            ],
        }
        return JSONResponse(status_code=200, content=payload)
    except Exception:
        logger.exception("Failed to list tenants")
        raise HTTPException(status_code=500, detail="Internal server error")

# API: get tenant
@app.get("/api/tenants/{tenant_id}")
def api_get_tenant(tenant_id: int, _: None = Depends(api_key_auth)) -> JSONResponse:
    try:
        t = get_tenant(tenant_id)
        if not t:
            raise HTTPException(status_code=404, detail="Tenant not found")
        payload = {
            "id": t.id,
            "name": t.name,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "last_activity_at": t.last_activity_at.isoformat() if t.last_activity_at else None,
            "total_events": t.total_events,
        }
        return JSONResponse(status_code=200, content=payload)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch tenant %s", tenant_id)
        raise HTTPException(status_code=500, detail="Internal server error")

# Frontend HTML (single-page, embedded React via CDN)
@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    # For this single-file demo we inject the API key into the page from env var.
    # In production, avoid embedding secrets in client-side HTML.
    api_key = settings.api_key
    html = f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>THE13TH - Tenants</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    /* small CSS overrides for the theme */
    body {{ background-color: #F4F6F8; color: #2A2A2F; font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; }}
    .app-shell {{ max-width: 1024px; margin: 0 auto; padding: 24px; }}
    .card {{ background: white; padding: 16px; border-radius: 16px; box-shadow: 0 6px 18px rgba(0,0,0,0.04); border: 1px solid #F3F4F6; }}
    .btn {{ background-color: #6D28D9; color: white; padding: 8px 12px; border-radius: 10px; text-decoration: none; display: inline-block; }}
  </style>
  <!-- React & ReactDOM from CDN -->
  <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
</head>
<body>
  <div id="root"></div>

  <script>
  // Embedded client-side React (not using build tools) — small SPA
  const e = React.createElement;

  const API_KEY = "{api_key}";
  const API_BASE = '/api';

  function formatDate(iso) {{
    if (!iso) return '—';
    try {{
      const d = new Date(iso);
      return d.toLocaleString();
    }} catch (err) {{
      return iso;
    }}
  }}

  function TenantCard({{ tenant }}) {{
    const statusClass = tenant.status === 'active' ? 'text-green-600 font-semibold' : tenant.status === 'paused' ? 'text-yellow-600 font-semibold' : 'text-red-600 font-semibold';
    return e('div', {{ className: 'card' }},
      e('div', {{ style: {{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}, className: 'mb-3' }},
        e('h3', {{ className: 'text-lg font-semibold' }}, tenant.name),
        e('div', {{ className: statusClass }}, tenant.status)
      ),
      e('div', {{ className: 'text-sm text-gray-500 mb-1' }}, 'Events: ' + tenant.total_events),
      e('div', {{ className: 'text-sm text-gray-500' }}, 'Last activity: ' + formatDate(tenant.last_activity_at)),
      e('div', {{ style: {{ marginTop: 12 }} }}, e('a', {{ className: 'btn', href: '#', onClick: (ev) => {{ ev.preventDefault(); alert('Tenant details not implemented in this single-file demo.'); }} }}, 'Open'))
    );
  }

  function App() {{
    const [tenants, setTenants] = React.useState([]);
    const [total, setTotal] = React.useState(0);
    const [loading, setLoading] = React.useState(true);
    const [error, setError] = React.useState(null);

    React.useEffect(() => {{
      let mounted = true;
      async function fetchTenants() {{
        try {{
          setLoading(true);
          const res = await fetch(API_BASE + '/tenants?limit=200', {{ headers: {{ 'Content-Type': 'application/json', 'X-API-Key': API_KEY }} }});
          if (!res.ok) {{
            const payload = await res.json().catch(() => ({{}}));
            throw new Error(payload.detail || ('HTTP ' + res.status));
          }}
          const data = await res.json();
          if (!mounted) return;
          setTenants(data.items || []);
          setTotal(data.total || 0);
        }} catch (err) {{
          console.error(err);
          setError(err.message);
        }} finally {{
          if (mounted) setLoading(false);
        }}
      }}
      fetchTenants();
      return () => {{ mounted = false; }};
    }}, []);

    return e('div', {{ className: 'app-shell' }},
      e('header', {{ className: 'flex items-center justify-between mb-6' }},
        e('div', {{ className: 'text-2xl font-bold' }}, 'THE13TH Intelligence Dashboard'),
        e('div', null, e('a', {{ className: 'btn', href: '#' }}, 'Dashboard'))
      ),
      e('main', null,
        e('div', {{ className: 'mb-4' }}, e('h2', {{ className: 'text-xl font-bold' }}, 'Tenants'), e('p', {{ className: 'text-sm text-gray-500' }}, 'Total tenants: ' + total)),
        loading && e('div', {{ className: 'text-sm text-gray-500' }}, 'Loading tenants…'),
        error && e('div', {{ className: 'text-sm text-red-600' }}, 'Error: ' + error),
        e('div', {{ className: 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4' }},
          tenants.map(t => e(TenantCard, {{ key: t.id, tenant: t }}))
        )
      )
    );
  }

  const root = ReactDOM.createRoot(document.getElementById('root'));
  root.render(e(App));
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html, status_code=200)

# Health endpoint
@app.get('/healthz')
def healthz() -> JSONResponse:
    return JSONResponse(status_code=200, content={"status": "ok", "app": "THE13TH"})

# ---------------------------
# CLI-run guard
# ---------------------------

if __name__ == '__main__':
    # Allow running via `python the13th_single_script.py`
    import uvicorn

    logger.info("Starting THE13TH single-file app on %s:%d", settings.host, settings.port)
    uvicorn.run("the13th_single_script:app", host=settings.host, port=settings.port, reload=True)
