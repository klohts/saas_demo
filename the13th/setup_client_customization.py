#!/usr/bin/env python3
"""
Setup Script — THE13TH Client Customization Layer (Final Polished Version)
Creates all directories and files under /home/hp/AIAutomationProjects/saas_demo/the13th/
Fully Pydantic v2–compliant and ready to run.
"""

import os
from pathlib import Path

def write_file(path: Path, content: str, binary: bool = False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        path.write_bytes(content)
    else:
        path.write_text(content.strip() + "\n")
    print(f"✅ Created: {path}")

BASE_DIR = Path("/home/hp/AIAutomationProjects/saas_demo/the13th")

# ---------------------- FULL APP CODE ----------------------
app_code = '''
from __future__ import annotations
import os, sys, logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import FastAPI, HTTPException, status, Request, Response, Header, Body, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlmodel import SQLModel, Field as ORMField, create_engine, Session, select, col
from starlette.middleware.base import BaseHTTPMiddleware

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
ASSETS_DIR = BASE_DIR / "assets"
for d in [DATA_DIR, TEMPLATES_DIR, ASSETS_DIR / "clients" / "default"]:
    d.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("CC_DATABASE_URL", f"sqlite:///{DATA_DIR / 'clients.db'}")
API_KEY = os.getenv("CC_API_KEY", "dev-default-api-key")
ADMIN_USERNAME = os.getenv("CC_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("CC_ADMIN_PASS", "adminpass")
RATE_LIMIT_PER_MIN = int(os.getenv("CC_RATE_LIMIT_PER_MIN", "60"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("client_customization")

class Client(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = ORMField(default=None, primary_key=True)
    client_id: str = ORMField(index=True, nullable=False, sa_column_kwargs={"unique": True})
    name: str = ORMField(index=True, nullable=False)
    description: Optional[str] = None
    integrations: Optional[str] = None
    branding_logo: Optional[str] = None
    branding_color: Optional[str] = None
    templates_path: Optional[str] = None
    created_at: datetime = ORMField(default_factory=datetime.utcnow)
    updated_at: datetime = ORMField(default_factory=datetime.utcnow)

class ClientCreate(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=64, json_schema_extra={"strip_whitespace": True})
    name: str = Field(..., min_length=1, max_length=128, json_schema_extra={"strip_whitespace": True})
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
    name: Optional[str] = Field(None, min_length=1, max_length=128, json_schema_extra={"strip_whitespace": True})
    description: Optional[str] = None
    integrations: Optional[Dict[str, Any]] = None
    branding_logo: Optional[str] = None
    branding_color: Optional[str] = None
    templates_path: Optional[str] = None

class RenderRequest(BaseModel):
    variables: Dict[str, Any] = Field(default_factory=dict)
    template_name: Optional[str] = "email_response.jinja2"

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})

def init_db():
    SQLModel.metadata.create_all(engine)
    logger.info("Database ready: %s", DATABASE_URL)

def get_session():
    return Session(engine)

security_basic = HTTPBasic()

def require_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")

def require_basic_auth(credentials: HTTPBasicCredentials = Depends(security_basic)):
    if credentials.username != ADMIN_USERNAME or credentials.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")

class SimpleRateLimiter(BaseHTTPMiddleware):
    def __init__(self, app, max_per_min=60):
        super().__init__(app)
        self.max_per_min = max_per_min
        self.storage: Dict[str, Dict[str, Any]] = {}

    async def dispatch(self, request, call_next):
        ip = request.client.host if request.client else "unknown"
        now = datetime.utcnow()
        bucket = self.storage.get(ip)
        if bucket is None or now >= bucket["reset_at"]:
            bucket = {"count": 0, "reset_at": now + timedelta(minutes=1)}
            self.storage[ip] = bucket
        bucket["count"] += 1
        if bucket["count"] > self.max_per_min:
            return JSONResponse({"detail": "Rate limit exceeded"}, 429)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_per_min)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.max_per_min - bucket["count"]))
        response.headers["X-RateLimit-Reset"] = bucket["reset_at"].isoformat()
        return response

app = FastAPI(title="THE13TH Client Customization", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(SimpleRateLimiter, max_per_min=RATE_LIMIT_PER_MIN)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.update({
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
    })
    return resp

@app.get("/", include_in_schema=False)
def root():
    return {"message": "THE13TH Client Customization Service is running", "docs": "/docs"}

@app.get("/healthz")
def healthz():
    return {"status": "ok", "app": "THE13TH Client Customization"}

@app.post("/api/clients", response_model=ClientRead)
def create_client(payload: ClientCreate, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    import json
    with get_session() as sess:
        if sess.exec(select(Client).where(Client.client_id == payload.client_id)).first():
            raise HTTPException(400, "client_id exists")
        row = Client(
            client_id=payload.client_id,
            name=payload.name,
            description=payload.description,
            integrations=json.dumps(payload.integrations or {}),
            branding_logo=payload.branding_logo,
            branding_color=payload.branding_color,
            templates_path=payload.templates_path,
        )
        sess.add(row)
        sess.commit()
        sess.refresh(row)
        return row

@app.get("/api/clients", response_model=list[ClientRead])
def list_clients(x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    with get_session() as sess:
        rows = sess.exec(select(Client)).all()
        import json
        out = []
        for r in rows:
            item = r.dict()
            item["integrations"] = json.loads(r.integrations or "{}")
            out.append(item)
        return out

if __name__ == "__main__":
    import uvicorn
    init_db()
    uvicorn.run("client_customization_app:app", host="0.0.0.0", port=int(os.getenv("PORT", "8001")))
'''

write_file(BASE_DIR / "client_customization_app.py", app_code)

# Template file
write_file(BASE_DIR / "templates" / "email_response.jinja2", """<!doctype html><html><body><h2>{{ client_name }}</h2><p>{{ body_text or 'Hello there!' }}</p></body></html>""")

# Dockerfile
write_file(BASE_DIR / "Dockerfile", """FROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nCMD [\"uvicorn\", \"client_customization_app:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8001\"]""")

# Fixed multiline requirements
write_file(BASE_DIR / "requirements.txt", """fastapi\nsqlmodel\nuvicorn[standard]\njinja2\npydantic\npytest\nhttpx\n""")

# Environment file
write_file(BASE_DIR / ".env.example", """CC_DATABASE_URL=sqlite:///data/clients.db\nCC_API_KEY=testkey\nCC_ADMIN_USER=admin\nCC_ADMIN_PASS=adminpass\nPORT=8001\n""")

# README
write_file(BASE_DIR / "README_CLIENT_CUSTOMIZATION.md", "Run with: python client_customization_app.py and visit http://localhost:8001/docs")

print(f"\n🎯 All files created successfully under {BASE_DIR}")
print("Run the app with:\n  cd /home/hp/AIAutomationProjects/saas_demo/the13th && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python client_customization_app.py")
