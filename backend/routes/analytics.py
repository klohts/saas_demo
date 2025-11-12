# backend/routes/analytics.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List
from backend.core.analytics import get_engine

router = APIRouter()
engine = get_engine()

# WebSocket broadcast manager (simple, in-memory)
class WSManager:
    def __init__(self):
        self._conns: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._conns.append(ws)

    def disconnect(self, ws: WebSocket):
        try:
            self._conns.remove(ws)
        except ValueError:
            pass

    async def broadcast(self, message):
        for c in list(self._conns):
            try:
                await c.send_json(message)
            except Exception:
                try:
                    self._conns.remove(c)
                except Exception:
                    pass

ws_mgr = WSManager()

class EventIn(BaseModel):
    user: str
    action: str

@router.post("/event")
async def post_event(e: EventIn):
    rec = engine.record_event(e.user, e.action)
    # broadcast to connected clients
    await ws_mgr.broadcast({"type":"event","data":rec})
    return {"status":"ok","event":rec}

@router.get("/scores")
def scores():
    return engine.get_scores()

@router.get("/timeseries")
def timeseries():
    return engine.get_timeseries()

@router.get("/users")
def users():
    return engine.get_users()

@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_mgr.connect(ws)
    try:
        while True:
            # keep alive; client may send pings
            _ = await ws.receive_text()
    except WebSocketDisconnect:
        ws_mgr.disconnect(ws)
