
import os
import logging
import time
from typing import Dict
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from .schemas import EventPayload
from .auth import require_basic_auth

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("the13th")

app = FastAPI(title="THE13TH", version="0.1.0")

@app.get("/api/healthz")
def healthz():
    return {"status": "ok", "app": "THE13TH"}

RATE_LIMIT = int(os.getenv("RATE_LIMIT_COUNT", "30"))
RATE_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
_rate_store: Dict[str, Dict[str, int]] = {}


def _rate_check(ip: str):
    now = int(time.time())
    rec = _rate_store.get(ip)
    if not rec:
        _rate_store[ip] = {"count": 1, "start": now}
        return
    start = rec["start"]
    if now - start > RATE_WINDOW:
        _rate_store[ip] = {"count": 1, "start": now}
        return
    if rec["count"] >= RATE_LIMIT:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
    rec["count"] += 1


@app.post("/api/events")
async def create_event(request: Request, payload: EventPayload, authorized: bool = Depends(require_basic_auth)):
    client_ip = request.client.host if request.client else "unknown"
    _rate_check(client_ip)

    try:
        logger.info("Received event: source=%s message=%s", payload.source, payload.message)
        return JSONResponse({"status": "accepted"}, status_code=status.HTTP_202_ACCEPTED)
    except ValidationError as e:
        logger.warning("Validation error: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        logger.exception("Unhandled error in create_event")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error")

# Serve static frontend (built into ./dist)
dist_path = os.path.join(os.path.dirname(__file__), "dist")
if os.path.isdir(dist_path):
    app.mount("/", StaticFiles(directory=dist_path, html=True), name="frontend")
    logger.info("Mounted frontend static files from %s", dist_path)
else:
    logger.warning("No frontend build found at %s — index will redirect to health", dist_path)
    @app.get("/")
    def index_redirect():
        return RedirectResponse(url="/api/healthz")
