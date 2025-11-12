#!/usr/bin/env python3
"""
setup_control_core.py

Single-script generator that creates a standalone Control Core microservice for THE13TH.
It writes files under:
  /home/hp/AIAutomationProjects/saas_demo/the13th/control_core/

Files created:
  - control_core/control_core_app.py  (main FastAPI app)
  - control_core/core_models.py       (shared Pydantic models)
  - control_core/core_utils.py        (auth, http client helper, logging)
  - control_core/.env.example
  - control_core/requirements.txt
  - control_core/Dockerfile
  - control_core/README_CONTROL_CORE.md

Usage:
  python setup_control_core.py

After creation, run locally:
  cd /home/hp/AIAutomationProjects/saas_demo/the13th/control_core
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  cp .env.example .env && export $(cat .env | xargs)
  python control_core_app.py

Service purpose summary:
- Central orchestration between Client Customization and App Intelligence services
- Validates internal system API key (CC_SYS_API_KEY)
- Forwards/normalizes events and exposes aggregation endpoints
- Uses httpx with timeouts and retries for robust inter-service calls

Design choices:
- Keep code single-file + small module files for clarity
- Use environment variables for secrets
- Light-weight, production-friendly defaults (timeouts, retries)
"""
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime

ROOT = Path('/home/hp/AIAutomationProjects/saas_demo/the13th')
TARGET = ROOT / 'control_core'
TARGET.mkdir(parents=True, exist_ok=True)

# Files content
control_core_app = '''from __future__ import annotations
import os
import logging
from pathlib import Path
from typing import List
from fastapi import FastAPI, Header, HTTPException, status, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from core_models import EventCreate, EventRead, AggregateReport
from core_utils import require_sys_api_key, get_http_client

# Config
BASE_DIR = Path(__file__).resolve().parent
CLIENT_SERVICE_URL = os.getenv('CC_CLIENT_SERVICE_URL', 'http://localhost:8001')
INTELLIGENCE_SERVICE_URL = os.getenv('CC_INTELLIGENCE_SERVICE_URL', 'http://localhost:8011')
SYS_API_KEY = os.getenv('CC_SYS_API_KEY', 'supersecret_sys_key')
HTTP_TIMEOUT = int(os.getenv('CC_HTTP_TIMEOUT', '10'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('control_core')

app = FastAPI(title='THE13TH — Control Core', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('CC_CORS_ORIGINS','*').split(','), allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

@app.exception_handler(Exception)
def _exc(request: Request, exc: Exception):
    logger.exception('Unhandled exception')
    return JSONResponse({'detail': 'Internal Server Error'}, status_code=500)

# Health
@app.get('/healthz')
def health():
    return {'status':'ok','app':'THE13TH Control Core'}

# Ingest an event from external services — validate sys key and forward normalized event to intelligence service
@app.post('/api/events', response_model=EventRead)
async def ingest_event(payload: EventCreate, x_sys_api_key: str = Header(None)):
    require_sys_api_key(x_sys_api_key)
    # normalize/timestamp
    payload.timestamp = payload.timestamp or datetime.utcnow().isoformat()
    # forward to intelligence service
    async with get_http_client(timeout=HTTP_TIMEOUT) as client:
        try:
            r = await client.post(f"{INTELLIGENCE_SERVICE_URL}/api/events", json=payload.dict(), headers={'X-SYS-API-KEY': SYS_API_KEY})
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error('Upstream responded: %s %s', e.response.status_code, e.response.text)
            raise HTTPException(status_code=502, detail='Upstream error')
        except Exception as e:
            logger.exception('Failed to forward event')
            raise HTTPException(status_code=502, detail='Upstream unreachable')
        data = r.json()
    return {**payload.dict(), 'id': data.get('id'), 'created_at': data.get('created_at')}

# Aggregate report endpoint — returns simple aggregates from intelligence service
@app.get('/api/reports/summary', response_model=AggregateReport)
async def reports_summary(x_sys_api_key: str = Header(None)):
    require_sys_api_key(x_sys_api_key)
    async with get_http_client(timeout=HTTP_TIMEOUT) as client:
        r = await client.get(f"{INTELLIGENCE_SERVICE_URL}/api/insights/summary", headers={'X-SYS-API-KEY': SYS_API_KEY})
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail='Upstream error')
        return r.json()

# Proxy read endpoints
@app.get('/api/clients')
async def proxy_clients(x_sys_api_key: str = Header(None)):
    require_sys_api_key(x_sys_api_key)
    async with get_http_client(timeout=HTTP_TIMEOUT) as client:
        r = await client.get(f"{CLIENT_SERVICE_URL}/api/clients", headers={'X-API-KEY': os.getenv('CC_CLIENT_API_KEY', '')})
        r.raise_for_status()
        return r.json()

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('control_core_app:app', host='0.0.0.0', port=int(os.getenv('CC_PORT','8021')), reload=os.getenv('CC_DEV_RELOAD','false').lower() in ('1','true'))
'''

core_models = '''from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class EventCreate(BaseModel):
    client_id: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)
    user: Optional[str]
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    timestamp: Optional[str] = None

class EventRead(EventCreate):
    id: int
    created_at: str

class AggregateReport(BaseModel):
    total_events: int
    unique_clients: int
    top_actions: List[Dict[str, Any]] = []
'''

core_utils = '''from __future__ import annotations
import os
from fastapi import Header, HTTPException, status
import httpx
from contextlib import asynccontextmanager

SYS_API_KEY = os.getenv('CC_SYS_API_KEY', 'supersecret_sys_key')

def require_sys_api_key(x_sys_api_key: str | None = Header(None)):
    if x_sys_api_key is None or x_sys_api_key != SYS_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid system API key')

@asynccontextmanager
async def get_http_client(timeout: int = 10):
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=25)
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        yield client
'''

env_example = '''# Control Core example environment
CC_PORT=8021
CC_SYS_API_KEY=supersecret_sys_key
CC_CLIENT_SERVICE_URL=http://localhost:8001
CC_INTELLIGENCE_SERVICE_URL=http://localhost:8011
CC_CLIENT_API_KEY=dev-default-api-key
CC_HTTP_TIMEOUT=10
CC_CORS_ORIGINS=*
CC_DEV_RELOAD=false
'''

requirements = '''fastapi
uvicorn[standard]
httpx
pydantic
'''

dockerfile = '''FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONUNBUFFERED=1
EXPOSE 8021
CMD ["python","control_core_app.py"]
'''

readme = '''# THE13TH Control Core

Standalone Control Core microservice to orchestrate Client Customization and App Intelligence.

Files created:
- control_core_app.py
- core_models.py
- core_utils.py
- .env.example
- requirements.txt
- Dockerfile

Run locally:
```bash
cd control_core
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && export $(cat .env | xargs)
python control_core_app.py
```

APIs:
- POST /api/events  — ingest event (requires X-SYS-API-KEY)
- GET /api/reports/summary — fetch summary from intelligence service
- GET /api/clients — proxy client listing from client service

Security: uses CC_SYS_API_KEY for internal authentication.
'''

# Write files
(TARGET / 'control_core_app.py').write_text(control_core_app)
(TARGET / 'core_models.py').write_text(core_models)
(TARGET / 'core_utils.py').write_text(core_utils)
(TARGET / '.env.example').write_text(env_example)
(TARGET / 'requirements.txt').write_text(requirements)
(TARGET / 'Dockerfile').write_text(dockerfile)
(TARGET / 'README_CONTROL_CORE.md').write_text(readme)

print('✅ Created control core files under:', TARGET)
print('Run:')
print('  cd', TARGET)
print('  python -m venv .venv && source .venv/bin/activate')
print('  pip install -r requirements.txt')
print('  cp .env.example .env && export $(cat .env | xargs)')
print('  python control_core_app.py')
""
