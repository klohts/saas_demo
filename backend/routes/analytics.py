from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
from pydantic import BaseModel
from backend.core.analytics import get_engine

router = APIRouter()
engine = get_engine()

# WebSocket connection manager
class WSManager:
    def __init__(self):
        self.connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self.connections.remove(ws)

    async def broadcast(self, message: dict):
        for ws in self.connections:
            await ws.send_json(message)


ws_manager = WSManager()


class EventIn(BaseModel):
    user: str
    action: str


@router.post("/event")
async def event(e: EventIn):
    evt = engine.record_event(e.user, e.action)
    await ws_manager.broadcast({"type": "event", "data": evt})
    return {"status": "ok"}


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
async def ws_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
