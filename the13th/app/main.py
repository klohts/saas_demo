from fastapi import FastAPI, APIRouter, Request, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any
import os, asyncio, json, logging

logger = logging.getLogger("the13th")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

app = FastAPI(title="THE13TH", version="1.0")
api = APIRouter(prefix="/api")

# --- broadcaster (simple memory-based) ---
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []
        self.lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self.lock:
            self.active.append(ws)
        logger.info("WS connected (%d total)", len(self.active))

    async def disconnect(self, ws: WebSocket):
        async with self.lock:
            if ws in self.active:
                self.active.remove(ws)
        logger.info("WS disconnected (%d total)", len(self.active))

    async def broadcast(self, message: Dict[str, Any]):
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

@api.post("/events")
async def post_event(payload: Dict[str, Any], background_tasks: BackgroundTasks):
    evt = {
        "type": payload.get("type", "event"),
        "timestamp": payload.get("timestamp"),
        "data": payload.get("data", payload),
    }
    background_tasks.add_task(manager.broadcast, evt)
    logger.info("Event queued: %s", evt.get("type"))
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
    return JSONResponse({"status": "ok", "app": "THE13TH"})

dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if os.path.isdir(dist_dir):
    static_dir = os.path.join(dist_dir, "assets")
    app.mount("/static", StaticFiles(directory=static_dir if os.path.isdir(static_dir) else dist_dir), name="static")

@app.get("/", include_in_schema=False)
async def serve_root():
    index = os.path.join(dist_dir, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return JSONResponse({"status": "ok"})

@app.get("/{path:path}", include_in_schema=False)
async def serve_spa(path: str, request: Request):
    if any(request.url.path.startswith(p) for p in ["/api", "/ws", "/static", "/healthz"]):
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    index = os.path.join(dist_dir, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return JSONResponse({"status": "ok"})

app.include_router(api)
