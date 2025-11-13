# saas_demo/the13th/app/main.py

import os
import json
import asyncio
import logging
from typing import List, Dict, Any

from fastapi import FastAPI, APIRouter, Request, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.tenants import router as tenants_router

# -------------------------------------------------
# Logging
# -------------------------------------------------
logger = logging.getLogger("the13th")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# -------------------------------------------------
# App
# -------------------------------------------------
app = FastAPI(title="THE13TH", version="1.0")

# Tenants API
app.include_router(tenants_router, prefix="/api/tenants")

# Shared API Router
api = APIRouter(prefix="/api")

# -------------------------------------------------
# WebSocket Broadcast Manager
# -------------------------------------------------
class ConnectionManager:
    def __init__(self) -> None:
        self.active: List[WebSocket] = []
        self.lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self.lock:
            self.active.append(ws)
        logger.info("WS connected (%d total)", len(self.active))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self.lock:
            if ws in self.active:
                self.active.remove(ws)
        logger.info("WS disconnected (%d total)", len(self.active))

    async def broadcast(self, message: Dict[str, Any]) -> None:
        data = json.dumps(message)
        async with self.lock:
            targets = list(self.active)

        for ws in targets:
            try:
                await ws.send_text(data)
            except Exception:
                logger.exception("WS send failed; removing client")
                await self.disconnect(ws)


manager = ConnectionManager()

# -------------------------------------------------
# Event API
# -------------------------------------------------
@api.post("/events")
async def post_event(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    evt = {
        "type": payload.get("type", "event"),
        "timestamp": payload.get("timestamp"),
        "data": payload.get("data", payload),
    }

    background_tasks.add_task(manager.broadcast, evt)
    logger.info("Event queued: %s", evt["type"])
    return JSONResponse({"status": "queued"}, status_code=202)

@app.websocket("/ws/events")
async def ws_events(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            _ = await ws.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(ws)
    except Exception:
        logger.exception("WS connection error")
        await manager.disconnect(ws)

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "app": "THE13TH"}

# -------------------------------------------------
# Static Frontend (Vite Build)
# -------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend", "dist"))
ASSETS_DIR = os.path.join(FRONTEND_DIST, "assets")

logger.info("Frontend dist path: %s", FRONTEND_DIST)
logger.info("Assets path: %s", ASSETS_DIR)

# Serve /assets (JS, CSS, images)
if os.path.isdir(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
    logger.info("Mounted /assets")

# Serve index.html for root
@app.get("/", include_in_schema=False)
async def serve_root():
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"status": "frontend_not_built"}, status_code=404)

# SPA Catch-All (must be last)
@app.get("/{path:path}", include_in_schema=False)
async def spa_catch_all(path: str, request: Request):
    # Don't interfere with APIs or sockets
    if request.url.path.startswith(("/api", "/ws", "/healthz", "/assets")):
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)

    return JSONResponse({"status": "frontend_not_built"}, status_code=404)

# -------------------------------------------------
# Plan API
# -------------------------------------------------
@api.get("/plan")
async def get_plan():
    return {
        "plan": "Free",
        "usage": {"cpu": 0.2, "ram": 128},
        "projects": [],
        "tenants": [],
        "status": "running",
    }

# Attach Router at end
app.include_router(api)
