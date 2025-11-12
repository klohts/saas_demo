#!/usr/bin/env python3
"""
Setup script — App Intelligence Engine (Phase 1)
Creates a full App Intelligence module under:

/home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/

Files created:
- /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/app_intelligence_app.py
- /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/models.py
- /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/requirements.txt
- /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/.env.example
- /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/README_APP_INTELLIGENCE.md
- /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/Dockerfile

Run this script once to generate the module. After generation:
  cd /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  python app_intelligence_app.py

The service will run on port defined in /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/.env.example

"""
from pathlib import Path
import os

BASE = Path("/home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence")
BASE.mkdir(parents=True, exist_ok=True)

def write(p: Path, content: str, binary: bool = False):
    p.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        p.write_bytes(content)
    else:
        p.write_text(content.strip()+"\n")
    print("✅ Created:", p)

# 1) app_intelligence_app.py
app_code = r'''#!/usr/bin/env python3
# File: /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/app_intelligence_app.py
"""
App Intelligence Engine - Phase 1
Endpoints:
- POST /api/events       -> ingest events
- GET  /api/insights/recent?limit=N -> recent events

Auth: X-SYS-API-KEY header must match THE13TH_SYS_KEY in .env
DB: SQLite (local) at /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/data/events.db
"""
from __future__ import annotations
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

# dotenv auto-load
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env.example", override=True)

from fastapi import FastAPI, Request, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlmodel import SQLModel, Field as ORMField, create_engine, Session, select

# Config
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("AI_DATABASE_URL", f"sqlite:///{DATA_DIR / 'events.db'}")
THE13TH_SYS_KEY = os.getenv("THE13TH_SYS_KEY", "sys-default-key")
PORT = int(os.getenv("PORT", "8011"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("app_intelligence")

# Models
class Event(SQLModel, table=True):
    id: Optional[int] = ORMField(default=None, primary_key=True)
    client_id: Optional[str] = ORMField(index=True, nullable=True)
    action: str = ORMField(nullable=False)
    user: Optional[str] = None
    metadata: Optional[str] = None
    created_at: datetime = ORMField(default_factory=datetime.utcnow)

class EventCreate(BaseModel):
    client_id: Optional[str] = Field(None, description="Optional client id")
    action: str = Field(..., min_length=1)
    user: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

# DB
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})

def init_db():
    SQLModel.metadata.create_all(engine)
    logger.info("Initialized DB at %s", DATABASE_URL)

def get_session():
    return Session(engine)

# App
app = FastAPI(title="THE13TH App Intelligence", version="1.0")

# Simple system key dependency
async def require_sys_key(x_sys_api_key: Optional[str] = Header(None)) -> None:
    if x_sys_api_key is None or x_sys_api_key != THE13TH_SYS_KEY:
        logger.warning("Invalid system API key attempt")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid system API key")

@app.on_event("startup")
def on_startup():
    init_db()

@app.post("/api/events")
def ingest_event(payload: EventCreate, x_sys_api_key: Optional[str] = Header(None)):
    # system-level key required
    if x_sys_api_key is None or x_sys_api_key != THE13TH_SYS_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid system API key")

    # normalize metadata to JSON string
    import json
    meta_str = json.dumps(payload.metadata or {})
    ev = Event(client_id=payload.client_id, action=payload.action, user=payload.user, metadata=meta_str)
    with get_session() as sess:
        sess.add(ev)
        sess.commit()
        sess.refresh(ev)
    logger.info("Ingested event id=%s action=%s client=%s", ev.id, ev.action, ev.client_id)
    return JSONResponse(status_code=201, content={"id": ev.id, "created_at": ev.created_at.isoformat()})

@app.get("/api/insights/recent")
def recent_events(limit: int = 20, x_sys_api_key: Optional[str] = Header(None)):
    if x_sys_api_key is None or x_sys_api_key != THE13TH_SYS_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid system API key")
    limit = max(1, min(100, limit))
    with get_session() as sess:
        q = select(Event).order_by(Event.created_at.desc()).limit(limit)
        rows = sess.exec(q).all()
        import json
        out = []
        for r in rows:
            out.append({
                "id": r.id,
                "client_id": r.client_id,
                "action": r.action,
                "user": r.user,
                "metadata": json.loads(r.metadata) if r.metadata else {},
                "created_at": r.created_at.isoformat(),
            })
    return JSONResponse(content={"events": out})

@app.get("/healthz")
def healthz():
    return {"status": "ok", "app": "THE13TH App Intelligence"}

if __name__ == "__main__":
    import uvicorn
    init_db()
    uvicorn.run("app_intelligence_app:app", host="0.0.0.0", port=PORT)
'''

write(BASE / "app_intelligence_app.py", app_code)

# 2) models.py (optional, simple copy)
models_code = r'''# File: /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/models.py
from sqlmodel import SQLModel, Field as ORMField
from typing import Optional
from datetime import datetime

class Event(SQLModel, table=True):
    id: Optional[int] = ORMField(default=None, primary_key=True)
    client_id: Optional[str] = ORMField(index=True, nullable=True)
    action: str = ORMField(nullable=False)
    user: Optional[str] = None
    metadata: Optional[str] = None
    created_at: datetime = ORMField(default_factory=datetime.utcnow)
'''

write(BASE / "models.py", models_code)

# 3) requirements.txt
reqs = """fastapi
uvicorn[standard]
sqlmodel
pydantic
python-dotenv
httpx
"""
write(BASE / "requirements.txt", reqs)

# 4) .env.example
env = """# File: /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/.env.example
AI_DATABASE_URL=sqlite:///data/events.db
THE13TH_SYS_KEY=supersecret_sys_key
PORT=8011
"""
write(BASE / ".env.example", env)

# 5) Dockerfile
docker = r'''# File: /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8011
EXPOSE 8011
CMD ["uvicorn", "app_intelligence_app:app", "--host", "0.0.0.0", "--port", "8011"]
'''
write(BASE / "Dockerfile", docker)

# 6) README
readme = r'''# THE13TH — App Intelligence Engine (Phase 1)

Files created under:
- /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/app_intelligence_app.py
- /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/models.py
- /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/requirements.txt
- /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/.env.example
- /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/Dockerfile

Quick start:

```bash
cd /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export $(cat .env | xargs)
python app_intelligence_app.py
```

API:
- POST /api/events  (requires header X-SYS-API-KEY)
- GET  /api/insights/recent (requires header X-SYS-API-KEY)
'''
write(BASE / "README_APP_INTELLIGENCE.md", readme)

print("\n🎯 App Intelligence module generated at:")
print(BASE)
print("Run instructions are in /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/README_APP_INTELLIGENCE.md")
