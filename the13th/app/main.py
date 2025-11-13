import os
import json
import asyncio
import logging
from typing import List, Dict, Any

from fastapi import FastAPI, APIRouter, Request, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.tenants import router as tenants_router

# -----------------------------------------------------
# Logging
# -----------------------------------------------------
logger = logging.getLogger("the13th")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# -----------------------------------------------------
# App
# -----------------------------------------------------
app = FastAPI(title="THE13TH", version="1.0")

# Tenants API
app.include_router(tenants_router, prefix="/api/tenants")

# Shared API Router
api = APIRouter(prefix="/api")

# -----------------------------------------------------
# WebSocket Broadcast Manager
# -----------------------------------------------------
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

# -----------------------------------------------------
# Event API
# -----------------------------------------------------
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

# -----------------------------------------------------
# Plan API — important for Dashboard
# -----------------------------------------------------
@api.get("/plan")
async def get_plan():
    return {
        "plan": "Free",
        "usage": {"cpu": 0.2, "ram": 128},
        "projects": [],
        "tenants": [],
        "status": "running",
    }

# -----------------------------------------------------
# IMPORTANT: Register all API routes BEFORE SPA mounts
# -----------------------------------------------------
app.include_router(api)

# -----------------------------------------------------
# Static Frontend (Vite Build)
# -----------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.abspath(os.path.join(BASE_DIR, "..", "frontend", "dist"))
ASSETS_DIR = os.path.join(FRONTEND_DIST, "assets")

logger.info("Frontend dist path: %s", FRONTEND_DIST)
logger.info("Assets path: %s", ASSETS_DIR)

# Serve /assets (JS, CSS)
if os.path.isdir(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
    logger.info("Mounted /assets")


# Serve index.html at root
@app.get("/", include_in_schema=False)
async def serve_index():
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    logger.warning("index.html not found at %s", index_path)
    return JSONResponse({"error": "frontend not built"}, status_code=404)
