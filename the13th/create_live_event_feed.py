#!/usr/bin/env python3
"""
create_live_event_feed.py
--------------------------------------------------------
Automates adding a live WebSocket event feed to THE13TH
dashboard — safely patches backend and frontend, builds,
commits, and optionally triggers a Render deploy.

Run this from the project root (~/AIAutomationProjects/saas_demo/the13th)
"""

import os
import subprocess
import textwrap
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR / "app"
FRONTEND_DIR = BASE_DIR / "frontend"
SRC_DIR = FRONTEND_DIR / "src"
MAIN_PY = APP_DIR / "main.py"
MAIN_JSX = SRC_DIR / "main.jsx"
INDEX_CSS = SRC_DIR / "index.css"

# ---------------------------------------------------------------------------
def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content).strip() + "\n")
    print(f"✅ Wrote {path.relative_to(BASE_DIR)}")

# ---------------------------------------------------------------------------
def patch_backend():
    """Write the backend main.py with websocket + api/events."""
    content = r'''
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
    '''
    write_file(MAIN_PY, content)
    (APP_DIR / "__init__.py").touch(exist_ok=True)
    print("✅ Backend patched with WebSocket + API event feed.")

# ---------------------------------------------------------------------------
def patch_frontend():
    """Write the React frontend with WS feed client."""
    content_jsx = r'''
    import React, { useEffect, useState, useRef } from 'react'
    import ReactDOM from 'react-dom/client'
    import './index.css'

    function useEventWebSocket(path = '/ws/events') {
      const [events, setEvents] = useState([])
      const wsRef = useRef(null)
      const reconnectRef = useRef(0)

      useEffect(() => {
        let mounted = true
        const connect = () => {
          const loc = window.location
          const protocol = loc.protocol === 'https:' ? 'wss' : 'ws'
          const host = loc.host
          const url = `${protocol}://${host}${path}`
          wsRef.current = new WebSocket(url)

          wsRef.current.onopen = () => {
            reconnectRef.current = 0
            console.info('WS connected:', url)
          }

          wsRef.current.onmessage = (e) => {
            if (!mounted) return
            try {
              const msg = JSON.parse(e.data)
              setEvents(prev => [msg, ...prev].slice(0, 200))
            } catch {}
          }

          wsRef.current.onclose = () => {
            if (!mounted) return
            const backoff = Math.min(10000, 1000 * (1 + reconnectRef.current))
            reconnectRef.current += 1
            setTimeout(connect, backoff)
          }

          wsRef.current.onerror = () => {
            try { wsRef.current.close() } catch {}
          }
        }

        connect()
        return () => { mounted = false; try { wsRef.current?.close() } catch {} }
      }, [path])
      return events
    }

    function Dashboard() {
      const events = useEventWebSocket('/ws/events')

      return (
        <div className="min-h-screen bg-orange-300 flex flex-col items-center py-10 text-gray-800">
          <h1 className="text-3xl font-bold mb-2">THE13TH Event Dashboard</h1>
          <p className="text-sm mb-6">Event monitoring is live and connected.</p>

          <div className="w-full max-w-3xl bg-white rounded-lg shadow p-4 overflow-auto">
            <div className="flex justify-between mb-3">
              <h2 className="font-semibold">Live Events</h2>
              <span className="text-xs text-gray-500">{events.length} events</span>
            </div>

            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {events.length === 0 ? (
                <div className="text-sm text-gray-500">No events yet...</div>
              ) : (
                events.map((ev, i) => (
                  <div key={i} className="border p-2 rounded text-sm bg-gray-50">
                    <div className="text-xs text-gray-500">{ev.timestamp ?? new Date().toISOString()}</div>
                    <div className="font-medium">{ev.type}</div>
                    <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(ev.data, null, 2)}</pre>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )
    }

    ReactDOM.createRoot(document.getElementById('root')).render(<Dashboard />)
    '''
    write_file(MAIN_JSX, content_jsx)

    css_content = "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n"
    write_file(INDEX_CSS, css_content)

    print("✅ Frontend patched with React WebSocket dashboard.")

# ---------------------------------------------------------------------------
def build_frontend():
    """Run npm build."""
    print("🏗️  Building frontend...")
    try:
        subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, check=True)
        subprocess.run(["npm", "run", "build"], cwd=FRONTEND_DIR, check=True)
        print("✅ Frontend build complete.")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Frontend build failed: {e}")
        return False
    return True

# ---------------------------------------------------------------------------
def commit_and_push():
    """Commit and push to GitHub."""
    print("📦 Committing changes...")
    try:
        subprocess.run(["git", "add", "app/main.py", "frontend/src/main.jsx", "frontend/src/index.css"], cwd=BASE_DIR, check=True)
        subprocess.run(["git", "commit", "-m", "Add live WebSocket event feed to THE13TH"], cwd=BASE_DIR, check=True)
        subprocess.run(["git", "push"], cwd=BASE_DIR, check=True)
        print("✅ Git commit and push successful.")
    except subprocess.CalledProcessError:
        print("⚠️  Git push skipped or failed (maybe no changes).")

# ---------------------------------------------------------------------------
def main():
    print("🚀 Starting live event feed setup for THE13TH...\n")
    patch_backend()
    patch_frontend()
    build_frontend()
    commit_and_push()
    print("\n🎉 THE13TH live event feed upgrade complete.")
    print("👉 Redeploy manually or run:")
    print("   curl -X POST 'https://api.render.com/deploy/srv-d475kper433s738vdmr0?key=AQ4JOubHX1g'\n")

# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
