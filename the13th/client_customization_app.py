#!/usr/bin/env python3
# File: /home/hp/AIAutomationProjects/saas_demo/the13th/client_customization_app.py
"""
THE13TH — Client Customization Service (corrected, Pydantic v2 compatible)

- Auto-loads /home/hp/AIAutomationProjects/saas_demo/the13th/.env.example via python-dotenv
- Pydantic v2-friendly Field usage (no constr())
- Safer Jinja2 template loading (always uses filesystem loader rooted at templates/)
- SQLModel table uses extend_existing to avoid reload errors
- Rate limiter, API-key auth, admin basic auth
"""

from __future__ import annotations
import os
import sys
import logging
import re
from re import Pattern
from pathlib import Path
from typing import Optional, Dict, Any

# dotenv auto-load
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
# Load environment from .env.example by default (override in production with real .env)
load_dotenv(dotenv_path=BASE_DIR / ".env.example", override=True)

from datetime import datetime, timedelta

from fastapi import (
    FastAPI,
    HTTPException,
    status,
    Request,
    Response,
    Header,
    Body,
    Depends,
)
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field
from sqlmodel import SQLModel, Field as ORMField, create_engine, Session, select, col
from starlette.middleware.base import BaseHTTPMiddleware
# === INTEGRATION: CONTROL CORE RELAY ===
# helpers for relaying events to Control Core (idempotent insertion)
import threading
import json
try:
    import httpx
except Exception:
    httpx = None

CC_CONTROL_CORE_URL = os.getenv('CC_CONTROL_CORE_URL', 'http://localhost:8021')
CC_SYS_API_KEY = os.getenv('CC_SYS_API_KEY', 'supersecret_sys_key')

def _post_to_control_core(payload: dict, timeout: int = 5) -> None:
    """Background post to Control Core using httpx (runs in thread)."""
    def _worker(p):
        try:
            if httpx is None:
                return
            with httpx.Client(timeout=timeout) as client:
                client.post(f"{CC_CONTROL_CORE_URL}/api/events", json=p, headers={"X-SYS-API-KEY": CC_SYS_API_KEY})
        except Exception:
            return
    threading.Thread(target=_worker, args=(payload,), daemon=True).start()
# === INTEGRATION: CONTROL CORE RELAY ===


# -------- CONFIG & LOGGING --------
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
ASSETS_DIR = BASE_DIR / "assets"

DATA_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
(ASSETS_DIR / "clients" / "default").mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("CC_DATABASE_URL", f"sqlite:///{DATA_DIR / 'clients.db'}")
API_KEY = os.getenv("CC_API_KEY", "dev-default-api-key")
ADMIN_USERNAME = os.getenv("CC_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("CC_ADMIN_PASS", "adminpass")
RATE_LIMIT_PER_MIN = int(os.getenv("CC_RATE_LIMIT_PER_MIN", "60"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("client_customization")

# -------- DATABASE MODELS --------
class Client(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = ORMField(default=None, primary_key=True)
    client_id: str = ORMField(index=True, nullable=False, sa_column_kwargs={"unique": True})
    name: str = ORMField(index=True, nullable=False)
    description: Optional[str] = None
    integrations: Optional[str] = None  # JSON string
    branding_logo: Optional[str] = None
    branding_color: Optional[str] = None
    templates_path: Optional[str] = None
    created_at: datetime = ORMField(default_factory=datetime.utcnow)
    updated_at: datetime = ORMField(default_factory=datetime.utcnow)


# -------- Pydantic Schemas (v2-friendly) --------
class ClientCreate(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    integrations: Optional[Dict[str, Any]] = Field(default_factory=dict)
    branding_logo: Optional[str] = None
    branding_color: Optional[str] = None
    templates_path: Optional[str] = None


class ClientRead(BaseModel):
    id: int
    client_id: str
    name: str
    description: Optional[str]
    integrations: Dict[str, Any]
    branding_logo: Optional[str]
    branding_color: Optional[str]
    templates_path: Optional[str]
    created_at: datetime
    updated_at: datetime


class ClientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None
    integrations: Optional[Dict[str, Any]] = None
    branding_logo: Optional[str] = None
    branding_color: Optional[str] = None
    templates_path: Optional[str] = None


class RenderRequest(BaseModel):
    variables: Dict[str, Any] = Field(default_factory=dict)
    template_name: Optional[str] = "email_response.jinja2"


# -------- DB ENGINE & UTIL --------
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    logger.info("Database initialized at %s", DATABASE_URL)


def get_session() -> Session:
    return Session(engine)


# -------- AUTH & SECURITY --------
security_basic = HTTPBasic()


def require_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    if x_api_key is None or x_api_key != API_KEY:
        logger.warning("Unauthorized api key attempt")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")


def require_basic_auth(credentials: HTTPBasicCredentials = Depends(security_basic)) -> None:
    if not (credentials.username == ADMIN_USERNAME and credentials.password == ADMIN_PASSWORD):
        logger.warning("Bad basic auth credentials for user=%s", credentials.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


# -------- SIMPLE RATE LIMITER MIDDLEWARE --------
class SimpleRateLimiter(BaseHTTPMiddleware):
    def __init__(self, app, max_per_min: int = 60):
        super().__init__(app)
        self.max_per_min = max_per_min
        self.storage: Dict[str, Dict[str, Any]] = {}

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        now = datetime.utcnow()
        bucket = self.storage.get(ip)
        if bucket is None or now >= bucket["reset_at"]:
            bucket = {"count": 0, "reset_at": now + timedelta(minutes=1)}
            self.storage[ip] = bucket
        bucket["count"] += 1
        if bucket["count"] > self.max_per_min:
            retry_after = int((bucket["reset_at"] - now).total_seconds())
            logger.debug("Rate limit exceeded for ip=%s", ip)
            return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429, headers={"Retry-After": str(retry_after)})
        # occasional cleanup
        if len(self.storage) > 10000:
            keys = [k for k, v in self.storage.items() if v["reset_at"] < now]
            for k in keys:
                del self.storage[k]
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_per_min)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.max_per_min - bucket["count"]))
        response.headers["X-RateLimit-Reset"] = bucket["reset_at"].isoformat()
        return response


# -------- APP & MIDDLEWARE --------
app = FastAPI(title="THE13TH — Client Customization Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CC_CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SimpleRateLimiter, max_per_min=RATE_LIMIT_PER_MIN)

# Jinja2 Env anchored at templates dir
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=select_autoescape(["html", "xml", "jinja2"]))
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # Minimal secure headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


# -------- HELPERS --------
def client_row_to_read(client: Client) -> ClientRead:
    import json
    integrations = {}
    if client.integrations:
        try:
            integrations = json.loads(client.integrations)
        except Exception:
            integrations = {}
    return ClientRead(
        id=client.id,
        client_id=client.client_id,
        name=client.name,
        description=client.description,
        integrations=integrations,
        branding_logo=client.branding_logo,
        branding_color=client.branding_color,
        templates_path=client.templates_path,
        created_at=client.created_at,
        updated_at=client.updated_at,
    )


# -------- ROUTES: HEALTH & INFO --------
@app.on_event("startup")
def startup_event():
    init_db()
    logger.info("Client Customization service startup complete. Templates dir: %s", TEMPLATES_DIR)


@app.get("/healthz", tags=["health"])
def healthz():
    return {"status": "ok", "app": "THE13TH Client Customization"}


@app.get("/", include_in_schema=False)
def home():
    return {"message": "Client Customization Service. Use /docs for API", "docs": "/docs"}


# -------- ROUTES: CLIENT CRUD --------
@app.post("/api/clients", response_model=ClientRead, status_code=201, tags=["clients"])
def create_client(payload: ClientCreate = Body(...), x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    now = datetime.utcnow()
    import json
    with get_session() as sess:
        existing = sess.exec(select(Client).where(Client.client_id == payload.client_id)).first()
        if existing:
            raise HTTPException(status_code=400, detail="client_id already exists")
        row = Client(
            client_id=payload.client_id,
            name=payload.name,
            description=payload.description,
            integrations=json.dumps(payload.integrations or {}),
            branding_logo=payload.branding_logo,
            branding_color=payload.branding_color,
            templates_path=payload.templates_path,
            created_at=now,
            updated_at=now,
        )
        sess.add(row)
        sess.commit()
        sess.refresh(row)
    # relay: notify Control Core about new client (best-effort, background)
    try:
        _post_to_control_core({
            'client_id': row.client_id,
            'action': 'client_created',
            'user': None,
            'metadata': {'name': row.name}
        })
    except Exception:
        pass

        logger.info("Created client %s (id=%s)", row.client_id, row.id)
        return client_row_to_read(row)


@app.get("/api/clients", response_model=list[ClientRead], tags=["clients"])
def list_clients(x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    with get_session() as sess:
        rows = sess.exec(select(Client).order_by(col(Client.created_at).desc())).all()
        return [client_row_to_read(r) for r in rows]


@app.get("/api/clients/{client_id}", response_model=ClientRead, tags=["clients"])
def get_client(client_id: str, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    with get_session() as sess:
        row = sess.exec(select(Client).where(Client.client_id == client_id)).first()
        if not row:
            raise HTTPException(status_code=404, detail="client not found")
        return client_row_to_read(row)


@app.put("/api/clients/{client_id}", response_model=ClientRead, tags=["clients"])
def update_client(client_id: str, payload: ClientUpdate, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    import json
    with get_session() as sess:
        row = sess.exec(select(Client).where(Client.client_id == client_id)).first()
        if not row:
            raise HTTPException(status_code=404, detail="client not found")
        updated = False
        for k, v in payload.dict(exclude_unset=True).items():
            if k == "integrations":
                setattr(row, "integrations", json.dumps(v or {}))
            else:
                setattr(row, k, v)
            updated = True
        if updated:
            row.updated_at = datetime.utcnow()
            sess.add(row)
            sess.commit()
            sess.refresh(row)
        logger.info("Updated client %s", client_id)
        return client_row_to_read(row)


@app.delete("/api/clients/{client_id}", status_code=204, tags=["clients"])
def delete_client(client_id: str, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    with get_session() as sess:
        row = sess.exec(select(Client).where(Client.client_id == client_id)).first()
        if not row:
            raise HTTPException(status_code=404, detail="client not found")
        sess.delete(row)
        sess.commit()
        logger.info("Deleted client %s", client_id)
        return Response(status_code=204)


# -------- TEMPLATE RENDERING ENDPOINT --------
@app.post("/api/clients/{client_id}/render", response_class=HTMLResponse, tags=["clients"])
def render_template_for_client(
    client_id: str,
    payload: RenderRequest,
    x_api_key: Optional[str] = Header(None),
):
    require_api_key(x_api_key)
    with get_session() as sess:
        client = sess.exec(select(Client).where(Client.client_id == client_id)).first()
        if not client:
            raise HTTPException(status_code=404, detail="client not found")

    template_name = payload.template_name or "email_response.jinja2"
    candidates = []
    if client.templates_path:
        candidates.append(Path(client.templates_path) / template_name)
        candidates.append(TEMPLATES_DIR / client.templates_path / template_name)
    candidates.append(TEMPLATES_DIR / template_name)

    selected_path: Optional[Path] = None
    for p in candidates:
        if p and Path(p).exists():
            selected_path = Path(p)
            break

    if selected_path is None:
        raise HTTPException(status_code=404, detail="Template not found")

    default_vars = {
        "client_name": client.name,
        "branding": {
            "logo": client.branding_logo or f"/assets/clients/default/logo.png",
            "color": client.branding_color or "#6b21a8",
        },
        "now": datetime.utcnow().isoformat(),
    }
    render_vars = {**default_vars, **(payload.variables or {})}

    # Always render via Jinja2 Environment rooted at TEMPLATES_DIR or the template's folder
    if selected_path.is_absolute() and not str(selected_path).startswith(str(TEMPLATES_DIR)):
        env = Environment(loader=FileSystemLoader(str(selected_path.parent)), autoescape=select_autoescape(["html", "xml", "jinja2"]))
        tpl = env.get_template(selected_path.name)
        html = tpl.render(**render_vars)
        return HTMLResponse(content=html)
    else:
        # template is within templates dir (or we treat it as such)
        env = jinja_env
        # selected relative to templates dir
        rel = selected_path.relative_to(TEMPLATES_DIR) if selected_path.is_relative_to(TEMPLATES_DIR) else selected_path.name
        tpl = env.get_template(str(rel))
        html = tpl.render(**render_vars)
        return HTMLResponse(content=html)


# -------- ADMIN UI: list clients (basic) --------
@app.get("/admin/clients", response_class=HTMLResponse, tags=["admin"])
def admin_clients_page(request: Request, credentials: HTTPBasicCredentials = Depends(security_basic)):
    if credentials.username != ADMIN_USERNAME or credentials.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    with get_session() as sess:
        rows = sess.exec(select(Client).order_by(col(Client.created_at).desc())).all()
        clients = [client_row_to_read(r) for r in rows]
    html = "<html><body><h1>Clients</h1><ul>"
    for c in clients:
        html += f"<li><b>{c.client_id}</b> — {c.name} (created {c.created_at.isoformat()})</li>"
    html += "</ul></body></html>"
    return HTMLResponse(content=html)


# -------- ERROR HANDLERS --------
@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning("HTTPException: %s %s", exc.status_code, exc.detail)
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.exception_handler(Exception)
def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse({"detail": "Internal Server Error"}, status_code=500)


# -------- MAIN --------
if __name__ == "__main__":
    import uvicorn

    # ensure DB exists before running (startup event also creates)
    init_db()

    uvicorn.run(
        "client_customization_app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8001")),
        reload=os.getenv("DEV_RELOAD", "false").lower() in ("1", "true"),
    )
