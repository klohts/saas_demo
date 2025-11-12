#!/usr/bin/env python3
"""
create_release_mvp.py

Scaffolds THE13TH MVP (Analytics + Tenant Panel + Live feed).
- Writes backend files (FastAPI) with WebSocket live updates.
- Writes frontend React (Vite) minimal app + components.
- Adds Dockerfile, .env.example, README.
- Optional build/start flags.

Place at: ~/AIAutomationProjects/saas_demo/create_release_mvp.py
Run: python create_release_mvp.py --build-frontend --start
"""

import os, sys, textwrap, subprocess, pathlib, argparse, logging, time, shutil

BASE = pathlib.Path(__file__).resolve().parent
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("mvp")

# -------------------------
# Helpers
# -------------------------
def write(path: str, content: str, mode: str = "w"):
    p = BASE / path
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, mode, encoding="utf-8") as f:
        f.write(textwrap.dedent(content).lstrip())
    log.info(f"wrote: {path}")

def run(cmd, cwd=None):
    log.info("run: " + " ".join(cmd))
    subprocess.run(cmd, cwd=cwd or BASE, check=True)

# -------------------------
# Backend files
# -------------------------
def create_backend():
    write("backend/core/analytics.py", """
    # backend/core/analytics.py
    # Simple SQLite-backed analytics engine with in-process event recording.

    import sqlite3
    import datetime
    import os
    import threading
    from typing import Dict, Any, List

    BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
    DATA_DIR = os.path.join(BASE_DIR, "backend_data")
    os.makedirs(DATA_DIR, exist_ok=True)
    DB_PATH = os.path.join(DATA_DIR, "analytics.db")

    _lock = threading.Lock()

    def _conn():
        return sqlite3.connect(DB_PATH, check_same_thread=False)

    class AnalyticsEngine:
        def __init__(self):
            self._init_db()

        def _init_db(self):
            with _lock:
                c = _conn().cursor()
                c.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, user TEXT, action TEXT, ts TEXT)")
                c.connection.commit()
                c.connection.close()

        def record_event(self, user: str, action: str) -> Dict[str, Any]:
            ts = datetime.datetime.utcnow().isoformat()
            with _lock:
                conn = _conn()
                conn.execute("INSERT INTO events (user, action, ts) VALUES (?, ?, ?)", (user, action, ts))
                conn.commit()
                conn.close()
            return {"user": user, "action": action, "ts": ts}

        def get_scores(self) -> Dict[str,int]:
            with _lock:
                conn = _conn()
                rows = conn.execute("SELECT user, COUNT(*) FROM events GROUP BY user").fetchall()
                conn.close()
            return {"scores": {r[0]: r[1] for r in rows}}

        def get_timeseries(self):
            with _lock:
                conn = _conn()
                rows = conn.execute("SELECT substr(ts,1,10) as d, COUNT(*) FROM events GROUP BY d ORDER BY d").fetchall()
                conn.close()
            return {"trend": {r[0]: r[1] for r in rows}}

        def get_users(self):
            with _lock:
                conn = _conn()
                rows = conn.execute("SELECT DISTINCT user FROM events").fetchall()
                conn.close()
            return {"users": [r[0] for r in rows]}

    # singleton
    engine = AnalyticsEngine()
    def get_engine():
        return engine
    """)

    write("backend/routes/analytics.py", """
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
    """)

    write("backend/main_app.py", """
    # backend/main_app.py
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from backend.routes import analytics

    app = FastAPI(title="THE13TH-MVP")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:9000", "http://127.0.0.1:9000", "https://the13th.onrender.com", "*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(analytics.router, prefix="/analytics")

    @app.get("/health")
    def health():
        import datetime
        return {"status":"ok", "timestamp": datetime.datetime.utcnow().isoformat()}
    """)

    # make package imports simpler
    write("backend/__init__.py", "")

# -------------------------
# Frontend files (minimal Vite + React)
# -------------------------
def create_frontend():
    # package.json (minimal)
    write("frontend/package.json", """
    {
      "name": "the13th-frontend",
      "version": "0.0.0",
      "private": true,
      "scripts": {
        "dev": "vite",
        "build": "vite build",
        "preview": "vite preview --port 9000"
      },
      "dependencies": {
        "react": "^18.2.0",
        "react-dom": "^18.2.0"
      },
      "devDependencies": {
        "vite": "^4.5.0",
        "@vitejs/plugin-react": "^4.0.0"
      }
    }
    """)

    write("frontend/index.html", """
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width,initial-scale=1.0" />
        <title>THE13TH — Live Analytics</title>
      </head>
      <body>
        <div id="root"></div>
        <script type="module" src="/src/main.jsx"></script>
      </body>
    </html>
    """)

    write("frontend/src/main.jsx", """
    import React from 'react'
    import { createRoot } from 'react-dom/client'
    import App from './App.jsx'
    import './index.css'

    createRoot(document.getElementById('root')).render(<App />)
    """)

    write("frontend/src/index.css", """
    html,body,#root { height:100%; margin:0; font-family: Inter, system-ui, Arial; background:#f7fafc; color:#111827;}
    .container { max-width:1024px; margin:24px auto; padding:16px; background: #ffffff; border-radius:8px; box-shadow: 0 8px 20px rgba(0,0,0,0.06);}
    .row { display:flex; gap:12px; align-items:center; }
    .col { flex:1; }
    pre { background:#0f172a; color:#e6eef8; padding:12px; border-radius:6px; overflow:auto; }
    """)

    write("frontend/src/api.js", """
    // frontend/src/api.js
    const API_BASE = (import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000") + "/analytics";

    async function safeFetch(path, opts){
      try{
        const res = await fetch(API_BASE + path, opts);
        if(!res.ok) throw new Error("HTTP " + res.status);
        return await res.json();
      }catch(e){
        console.error("api error", e);
        return { error: "Failed to fetch" };
      }
    }

    export async function fetchScores(){ return safeFetch("/scores"); }
    export async function fetchTrend(){ return safeFetch("/timeseries"); }
    export async function fetchUsers(){ return safeFetch("/users"); }
    export async function postEvent(user, action){
      return safeFetch("/event", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ user, action }) });
    }

    // Tenant / demo helper stubs (will be upgraded later)
    export async function listTenants(){
      return [{ id:1, name:"Default", plan:"starter" }];
    }
    export async function getTenant(id=1){
      const t = await listTenants(); return t.find(x=>x.id===id) || t[0];
    }
    export async function toggleDemo(){
      return { status:"ok", demo:true };
    }
    export async function demoStatus(){
      return { active:true };
    }
    """)

    write("frontend/src/components/TenantHeader.jsx", """
    import React from 'react'

    export default function TenantHeader({tenant, onToggleDemo}){
      return (
        <div className="row" style={{justifyContent:"space-between"}}>
          <div>
            <h2 style={{margin:0}}>{tenant?.name || "Tenant"}</h2>
            <small>Plan: {tenant?.plan || "Starter"}</small>
          </div>
          <div>
            <button onClick={onToggleDemo}>Toggle Demo</button>
          </div>
        </div>
      )
    }
    """)

    write("frontend/src/components/EventFeed.jsx", """
    import React, {useEffect, useState, useRef} from 'react'

    export default function EventFeed({wsUrl}){
      const [events, setEvents] = useState([]);
      const wsRef = useRef(null);

      useEffect(()=>{
        let mounted=true;
        const connect = ()=> {
          try{
            const proto = location.protocol === "https:" ? "wss" : "ws";
            const url = wsUrl || `${proto}://${location.hostname}:8000/analytics/ws`;
            const ws = new WebSocket(url);
            ws.onmessage = (ev)=>{
              try{
                const msg = JSON.parse(ev.data);
                if(msg?.type === "event"){
                  setEvents(prev => [msg.data, ...prev].slice(0,50));
                }
              }catch(e){}
            }
            ws.onopen = ()=> console.log("ws open", url);
            ws.onclose = ()=> setTimeout(connect, 2000);
            wsRef.current = ws;
          }catch(e){
            console.warn("ws err", e);
            setTimeout(connect, 2000);
          }
        }
        connect();
        return ()=> { mounted=false; if(wsRef.current) wsRef.current.close(); }
      }, [wsUrl]);

      return (
        <div>
          <h3>Live Events</h3>
          <ul>
            {events.map((e, i)=> <li key={i}><strong>{e.user}</strong> — {e.action} <small>({e.ts})</small></li>)}
          </ul>
        </div>
      )
    }
    """)

    write("frontend/src/App.jsx", """
    import React, {useEffect, useState} from "react";
    import { fetchScores, fetchTrend, fetchUsers, postEvent, listTenants, getTenant, toggleDemo } from "./api";
    import TenantHeader from "./components/TenantHeader";
    import EventFeed from "./components/EventFeed";

    export default function App(){
      const [scores, setScores] = useState({});
      const [trend, setTrend] = useState({});
      const [users, setUsers] = useState([]);
      const [tenant, setTenant] = useState(null);

      useEffect(()=>{ refreshAll(); }, []);

      async function refreshAll(){
        const s = await fetchScores(); if(!s.error) setScores(s.scores || s);
        const t = await fetchTrend(); if(!t.error) setTrend(t.trend || t);
        const u = await fetchUsers(); if(!u.error) setUsers(u.users || u);
        const tenants = await listTenants();
        setTenant(await getTenant(tenants[0]?.id));
      }

      async function sendEvent(){
        await postEvent("demo_user", "clicked_demo");
        await refreshAll();
      }

      async function onToggleDemo(){
        await toggleDemo();
        await refreshAll();
      }

      return (
        <div className="container">
          <TenantHeader tenant={tenant} onToggleDemo={onToggleDemo} />
          <div style={{marginTop:12}} className="row">
            <div className="col">
              <h3>Scores</h3>
              <pre>{JSON.stringify(scores, null, 2)}</pre>
              <button onClick={sendEvent}>Send test event</button>
            </div>
            <div className="col">
              <h3>Trend</h3>
              <pre>{JSON.stringify(trend, null, 2)}</pre>
            </div>
          </div>
          <div style={{marginTop:12}} className="row">
            <div className="col">
              <h3>Users</h3>
              <pre>{JSON.stringify(users, null, 2)}</pre>
            </div>
            <div className="col">
              <EventFeed />
            </div>
          </div>
        </div>
      )
    }
    """)

    # vite config (minimal)
    write("frontend/vite.config.js", """
    import { defineConfig } from "vite"
    import react from "@vitejs/plugin-react"

    export default defineConfig({
      plugins: [react()],
      server: { port: 9000 }
    })
    """)

# -------------------------
# Dockerfile, env, README
# -------------------------
def create_artifacts():
    write("Dockerfile", """
    FROM python:3.12-slim
    WORKDIR /app
    COPY . .
    RUN apt-get update && apt-get install -y curl nodejs npm build-essential --no-install-recommends || true
    RUN pip install --no-cache-dir fastapi uvicorn python-dotenv
    WORKDIR /app/frontend
    RUN npm install --legacy-peer-deps || true
    RUN npm run build || true
    WORKDIR /app
    EXPOSE 8000
    CMD ["uvicorn", "backend.main_app:app", "--host", "0.0.0.0", "--port", "8000"]
    """)

    write(".env.example", """
    # Example env vars
    ADMIN_EMAIL=admin@the13th.com
    SESSION_TIMEOUT=3600
    COOKIE_SECURE=0
    VITE_API_BASE=http://127.0.0.1:8000
    """)

    write("README.md", """
    THE13TH — MVP (Analytics + Live Feed + Tenant Panel)

    How to run locally:
      1. Python deps:
         python -m pip install -U fastapi uvicorn python-dotenv

      2. Frontend (optional dev):
         cd frontend
         npm install
         npm run dev   # -> http://localhost:9000

      3. Start backend:
         uvicorn backend.main_app:app --reload --port 8000

      4. Visit frontend: http://localhost:9000
         Frontend communicates with backend at VITE_API_BASE (see .env.example)

    Docker:
      docker build -t the13th-mvp:latest .
      docker run -p 8000:8000 the13th-mvp:latest
    """)

# -------------------------
# Entry / orchestration
# -------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", action="store_true", help="Start backend after creating files")
    parser.add_argument("--build-frontend", action="store_true", help="Run npm install && build in frontend (requires npm)")
    parser.add_argument("--docker", action="store_true", help="Build docker image (requires docker)")
    args = parser.parse_args()

    log.info("Creating THE13TH MVP scaffold...")
    create_backend()
    create_frontend()
    create_artifacts()
    log.info("Scaffold created. Files written.")

    if args.build_frontend:
        log.info("Building frontend (npm install && npm run build)...")
        try:
            run(["npm", "install"], cwd=BASE / "frontend")
            run(["npm", "run", "build"], cwd=BASE / "frontend")
            log.info("Frontend build complete.")
        except Exception as e:
            log.warning("Frontend build failed (npm or build issues): " + str(e))

    if args.docker:
        log.info("Building docker image the13th-mvp:latest ...")
        try:
            run(["docker", "build", "-t", "the13th-mvp:latest", "."], cwd=BASE)
            log.info("Docker build complete.")
        except Exception as e:
            log.warning("Docker build failed: " + str(e))

    if args.start:
        log.info("Starting backend (uvicorn backend.main_app:app --reload)...")
        try:
            # start uvicorn in the foreground
            run([sys.executable, "-m", "uvicorn", "backend.main_app:app", "--reload", "--port", "8000"], cwd=BASE)
        except KeyboardInterrupt:
            log.info("Stopped.")
        except Exception as e:
            log.warning("Failed to start uvicorn: " + str(e))

    log.info("Done — MVP scaffold ready. See README.md for running notes.")

if __name__ == "__main__":
    main()
