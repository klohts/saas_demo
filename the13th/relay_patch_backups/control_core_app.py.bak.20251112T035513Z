#!/usr/bin/env python3
"""
control_core_app.py

Upgraded Control Core (standalone FastAPI service) with background relay + retry queue.
Location (exact):
/home/hp/AIAutomationProjects/saas_demo/the13th/control_core/control_core_app.py

Features:
- /api/events (POST) accepts EventCreate and enqueues it for immediate relay to
  App Intelligence and Client Customization services.
- Relay runs in background worker(s) pushing to upstreams with retries (exponential backoff).
- Durable write-ahead log: enqueued events are appended to a JSONL file (relay_queue.jsonl)
  so restarts can resume processing.
- /api/reports/summary proxies to Intelligence service.
- /api/clients proxies to Client Customization service.
- /metrics returns simple relay metrics.

How to run (exact):
  cd /home/hp/AIAutomationProjects/saas_demo/the13th/control_core
  source .venv/bin/activate
  export $(grep -v '^#' .env | xargs)
  python control_core_app.py

Environment variables (see .env.example in same dir):
  CC_PORT=8021
  CC_SYS_API_KEY=supersecret_sys_key
  CC_CLIENT_SERVICE_URL=http://localhost:8001
  CC_INTELLIGENCE_SERVICE_URL=http://localhost:8011
  CC_CLIENT_API_KEY=dev-default-api-key
  CC_HTTP_TIMEOUT=10
  CC_RELAY_WORKERS=2
  CC_RELAY_MAX_RETRIES=5

Notes:
- Uses only standard libs + httpx + fastapi. Ensure requirements.txt installed.
- Durable queue file: relay_queue.jsonl in service dir. If file grows large, rotate externally.
"""
from __future__ import annotations
import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx

# allow imports from local module files (core_models/core_utils exist)
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core_models import EventCreate, EventRead, AggregateReport
from core_utils import require_sys_api_key

# --- CONFIG ---
PORT = int(os.getenv('CC_PORT', '8021'))
SYS_API_KEY = os.getenv('CC_SYS_API_KEY', 'supersecret_sys_key')
CLIENT_SERVICE_URL = os.getenv('CC_CLIENT_SERVICE_URL', 'http://localhost:8001')
INTELLIGENCE_SERVICE_URL = os.getenv('CC_INTELLIGENCE_SERVICE_URL', 'http://localhost:8011')
CLIENT_API_KEY = os.getenv('CC_CLIENT_API_KEY', '')
HTTP_TIMEOUT = int(os.getenv('CC_HTTP_TIMEOUT', '10'))
RELAY_WORKERS = int(os.getenv('CC_RELAY_WORKERS', '2'))
RELAY_MAX_RETRIES = int(os.getenv('CC_RELAY_MAX_RETRIES', '5'))
QUEUE_FILE = ROOT / 'relay_queue.jsonl'

# --- logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('control_core')

# --- FastAPI app ---
app = FastAPI(title='THE13TH Control Core (Upgraded Relay)', version='1.1.0')
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('CC_CORS_ORIGINS', '*').split(','), allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

# --- relay internals ---
relay_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
metrics = {
    'enqueued': 0,
    'processed': 0,
    'failed': 0,
}

# ensure queue file exists
QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
if not QUEUE_FILE.exists():
    QUEUE_FILE.write_text('')

# helper: durable enqueue (append to file + put to in-memory queue)
async def durable_enqueue(event: Dict[str, Any]) -> None:
    # add metadata
    event['_enqueued_at'] = datetime.now(timezone.utc).isoformat()
    event['_attempts'] = 0
    # append to JSONL for durability
    with QUEUE_FILE.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(event, default=str) + '\n')
    await relay_queue.put(event)
    metrics['enqueued'] += 1
    logger.debug('Enqueued event id=%s action=%s', event.get('client_id'), event.get('action'))

# helper: mark processed by rewriting queue file (simple approach: rewrite without processed)
def remove_from_queue_file(processed_event: Dict[str, Any]) -> None:
    try:
        lines = QUEUE_FILE.read_text(encoding='utf-8').splitlines()
        out_lines = []
        target_serial = json.dumps(processed_event, default=str)
        # We can't reliably match the entire JSON since attempts/timestamps differ. Instead remove by matching client_id+action+timestamp
        target_key = (processed_event.get('client_id'), processed_event.get('action'), processed_event.get('_enqueued_at'))
        for line in lines:
            try:
                obj = json.loads(line)
            except Exception:
                continue
            key = (obj.get('client_id'), obj.get('action'), obj.get('_enqueued_at'))
            if key == target_key:
                continue
            out_lines.append(line)
        QUEUE_FILE.write_text('\n'.join(out_lines) + ('\n' if out_lines else ''))
    except Exception as e:
        logger.exception('Failed updating queue file: %s', e)

# build http client
def make_client() -> httpx.AsyncClient:
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=50)
    return httpx.AsyncClient(timeout=httpx.Timeout(HTTP_TIMEOUT), limits=limits)

async def relay_worker(worker_id: int) -> None:
    logger.info('Relay worker %s started', worker_id)
    client = make_client()
    try:
        while True:
            event = await relay_queue.get()
            # attempt to send to both upstreams; errors are handled per-upstream
            metrics['processed'] += 1
            success_any = False
            # send to intelligence service
            try:
                r = await client.post(f"{INTELLIGENCE_SERVICE_URL}/api/events", json=event, headers={'X-SYS-API-KEY': SYS_API_KEY})
                r.raise_for_status()
                logger.info('Worker %s: forwarded to intelligence (status=%s)', worker_id, r.status_code)
                success_any = True
            except Exception as e:
                logger.warning('Worker %s: failed to forward to intelligence: %s', worker_id, e)
            # send to client customization (non-blocking)
            try:
                r2 = await client.post(f"{CLIENT_SERVICE_URL}/api/events", json=event, headers={'X-API-KEY': CLIENT_API_KEY})
                # Note: client customization may not expose /api/events; tolerate 404/401
                if r2.status_code in (200, 201):
                    logger.info('Worker %s: forwarded to client customization (status=%s)', worker_id, r2.status_code)
                    success_any = True
                else:
                    logger.debug('Worker %s: customization returned %s', worker_id, r2.status_code)
            except Exception as e:
                logger.warning('Worker %s: failed to forward to customization: %s', worker_id, e)

            if success_any:
                # remove from durable queue
                remove_from_queue_file(event)
            else:
                # retry logic: increase attempts and requeue with backoff up to max
                event['_attempts'] = event.get('_attempts', 0) + 1
                if event['_attempts'] > RELAY_MAX_RETRIES:
                    logger.error('Worker %s: dropping event after %s attempts: %s', worker_id, event['_attempts'], event)
                    metrics['failed'] += 1
                    remove_from_queue_file(event)
                else:
                    backoff = 2 ** event['_attempts']
                    logger.info('Worker %s: retrying event after %s seconds (attempt %s)', worker_id, backoff, event['_attempts'])
                    # re-append updated event to queue file
                    with QUEUE_FILE.open('a', encoding='utf-8') as fh:
                        fh.write(json.dumps(event, default=str) + '\n')
                    # schedule requeue after backoff
                    asyncio.get_event_loop().call_later(backoff, lambda ev=event: asyncio.create_task(relay_queue.put(ev)))
            relay_queue.task_done()
    finally:
        await client.aclose()

# startup: load any existing queue items from file into memory
async def load_persistent_queue() -> None:
    try:
        if QUEUE_FILE.exists():
            lines = QUEUE_FILE.read_text(encoding='utf-8').splitlines()
            for line in lines:
                try:
                    obj = json.loads(line)
                    # ensure required fields
                    if 'client_id' in obj and 'action' in obj:
                        # ensure attempts present
                        obj['_attempts'] = obj.get('_attempts', 0)
                        await relay_queue.put(obj)
                except Exception:
                    continue
            logger.info('Loaded %s items from persistent queue', relay_queue.qsize())
    except Exception as e:
        logger.exception('Failed loading persistent queue: %s', e)

# background startup tasks
@app.on_event('startup')
async def startup_event():
    # load persistent queue
    await load_persistent_queue()
    # start worker tasks
    for i in range(RELAY_WORKERS):
        asyncio.create_task(relay_worker(i+1))
    logger.info('Control Core relay started with %s workers', RELAY_WORKERS)

# --- Routes ---
@app.get('/healthz')
def health():
    return {'status': 'ok', 'app': 'THE13TH Control Core'}

@app.post('/api/events', response_model=EventRead)
async def ingest_event(payload: EventCreate, x_sys_api_key: Optional[str] = Header(None)):
    # validate system key
    try:
        require_sys_api_key(x_sys_api_key)
    except HTTPException as e:
        raise
    # normalize timestamp
    if not getattr(payload, 'timestamp', None):
        payload.timestamp = datetime.now(timezone.utc).isoformat()
    event_dict = payload.dict()
    # durable enqueue
    await durable_enqueue(event_dict)
    # Return accepted shape; id/created_at will be set by intelligence service when processed
    return EventRead(**{**event_dict, 'id': -1, 'created_at': payload.timestamp})

@app.get('/api/reports/summary', response_model=AggregateReport)
async def reports_summary(x_sys_api_key: Optional[str] = Header(None)):
    require_sys_api_key(x_sys_api_key)
    async with make_client() as client:
        r = await client.get(f"{INTELLIGENCE_SERVICE_URL}/api/insights/summary", headers={'X-SYS-API-KEY': SYS_API_KEY})
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail='Upstream error')
        return AggregateReport(**r.json())

@app.get('/api/clients')
async def proxy_clients(x_sys_api_key: Optional[str] = Header(None)):
    require_sys_api_key(x_sys_api_key)
    async with make_client() as client:
        r = await client.get(f"{CLIENT_SERVICE_URL}/api/clients", headers={'X-API-KEY': CLIENT_API_KEY})
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail='Upstream error')
        return r.json()

@app.get('/metrics')
def get_metrics():
    return metrics

# graceful shutdown: wait for queue to drain
@app.on_event('shutdown')
async def shutdown_event():
    logger.info('Shutdown: waiting for queue to drain')
    await relay_queue.join()
    logger.info('Queue drained; exiting')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('control_core_app:app', host='0.0.0.0', port=PORT)

# --- Unified Event Bus + System Overview Patch ---
from fastapi import Depends
import threading, sqlite3

# Persistent metrics store
METRICS_DB = Path(__file__).parent / 'data' / 'metrics.db'
METRICS_DB.parent.mkdir(parents=True, exist_ok=True)

def init_metrics():
    with sqlite3.connect(METRICS_DB) as db:
        db.execute('''CREATE TABLE IF NOT EXISTS metrics (key TEXT PRIMARY KEY, value INTEGER)''')
        db.execute('''INSERT OR IGNORE INTO metrics (key, value) VALUES ('total_events', 0)''')
        db.execute('''INSERT OR IGNORE INTO metrics (key, value) VALUES ('unique_clients', 0)''')
        db.commit()

def update_metric(key: str, delta: int = 1):
    with sqlite3.connect(METRICS_DB) as db:
        db.execute('UPDATE metrics SET value = value + ? WHERE key = ?', (delta, key))
        db.commit()

def get_metrics():
    with sqlite3.connect(METRICS_DB) as db:
        return dict(db.execute('SELECT key, value FROM metrics').fetchall())

@app.post('/api/events', tags=['events'])
async def unified_ingest(event: dict):
    import aiohttp
    update_metric('total_events', 1)
    client_id = event.get('client_id')
    if client_id:
        update_metric('unique_clients', 1)
    # Relay to intelligence service
    AI_URL = os.getenv('CC_APP_INTELLIGENCE_URL', 'http://localhost:8011/api/events')
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(AI_URL, json=event, timeout=5) as resp:
                logger.info(f'Relayed event to App Intelligence → {resp.status}')
        except Exception as e:
            logger.error(f'Failed to relay event → {e}')
    return {'status': 'queued', 'event': event}

@app.get('/api/system/overview', tags=['system'])
def system_overview():
    try:
        with httpx.Client(timeout=5) as client:
            cc = client.get('http://localhost:8001/healthz').json()
            ai = client.get('http://localhost:8011/healthz').json()
            ctrl = client.get('http://localhost:8021/healthz').json()
        metrics = get_metrics()
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'services': {'client_customization': cc, 'app_intelligence': ai, 'control_core': ctrl},
            'metrics': metrics
        }
    except Exception as e:
        return {'detail': str(e)}

@app.on_event('startup')
def _init_metrics():
    init_metrics()
    logger.info('✅ Metrics DB initialized.')

# --- End Patch ---
