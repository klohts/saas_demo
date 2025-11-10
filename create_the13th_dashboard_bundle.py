#!/usr/bin/env python3
"""
create_the13th_dashboard_bundle.py

Creates the THE13TH Admin Intelligence Dashboard bundle:
- main_admin_intel.py (FastAPI backend with WebSocket and rules API)
- rules.json
- web/admin_ui/ React + Vite project source files

Save this file to: saas_demo/create_the13th_dashboard_bundle.py
Run: python saas_demo/create_the13th_dashboard_bundle.py
"""

import os, stat, textwrap, json, sys

ROOT = os.path.abspath(os.path.join(os.getcwd(), "saas_demo"))
WEB = os.path.join(ROOT, "web", "admin_ui")
SRC = os.path.join(WEB, "src")
COMP = os.path.join(SRC, "components")

def ensure(path):
    os.makedirs(path, exist_ok=True)

def write(path, content, mode=0o644):
    ensure(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content).lstrip())
    os.chmod(path, mode)
    print("Wrote:", path)

def main():
    print("Creating THE13TH bundle under:", ROOT)
    ensure(ROOT); ensure(WEB); ensure(SRC); ensure(COMP)

    # main_admin_intel.py (backend)
    write(os.path.join(ROOT, "main_admin_intel.py"), r"""
    # main_admin_intel.py
    """
    + r'''
    # Full backend (same as provided earlier)
    import os
    import asyncio
    import sqlite3
    import logging
    from datetime import datetime, timezone
    from typing import Optional, List, Dict, Any
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse, HTMLResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
    import smtplib
    from email.message import EmailMessage
    import json
    import time
    import math
    from dotenv import load_dotenv

    load_dotenv()

    DB_PATH = os.environ.get("ADMIN_INTEL_DB", "admin_intel.db")
    POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "5"))
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER)
    ALERT_TO = os.environ.get("ALERT_TO", "rhettlohts@gmail.com")
    SCORE_THRESHOLD = float(os.environ.get("SCORE_THRESHOLD", "0.8"))
    RULES_FILE = os.environ.get("RULES_FILE", "rules.json")

    MAX_EMAIL_RETRIES = 3
    EMAIL_RETRY_BACKOFF_SEC = 3

    ACTION_BASE_SCORES = {
        "signup": 0.3,
        "login": 0.1,
        "password_reset": 0.25,
        "lead_hot": 0.95,
        "client_upgrade": 0.9,
        "billing_failure": 0.85,
        "suspicious_activity": 0.9,
        "api_error": 0.4,
        "high_value_action": 0.9,
    }

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger("admin_intel")

    app = FastAPI(title="THE13TH — Admin Intelligence (Core 2.5)")

    STATIC_DIR = os.path.join(os.path.dirname(__file__), "web", "admin_ui", "dist")
    if os.path.isdir(STATIC_DIR):
        app.mount("/intel/static", StaticFiles(directory=STATIC_DIR), name="static")

    def init_db():
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT,
                action TEXT NOT NULL,
                payload TEXT,
                timestamp REAL NOT NULL,
                processed INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER,
                action_type TEXT,
                details TEXT,
                timestamp REAL NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()
        logger.info("DB initialized at %s", DB_PATH)

    def insert_event(user: Optional[str], action: str, payload: Optional[Dict[str, Any]], timestamp: float):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO events (user, action, payload, timestamp, processed) VALUES (?, ?, ?, ?, 0)",
            (user, action, json.dumps(payload) if payload is not None else None, timestamp),
        )
        eid = cur.lastrowid
        conn.commit()
        conn.close()
        logger.debug("Inserted event id=%s action=%s user=%s", eid, action, user)
        return eid

    def fetch_unprocessed_events(limit: int = 50) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, user, action, payload, timestamp FROM events WHERE processed = 0 ORDER BY timestamp ASC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        events = []
        for r in rows:
            events.append({
                "id": r[0],
                "user": r[1],
                "action": r[2],
                "payload": json.loads(r[3]) if r[3] else None,
                "timestamp": r[4],
            })
        return events

    def mark_event_processed(event_id: int):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE events SET processed = 1 WHERE id = ?", (event_id,))
        conn.commit()
        conn.close()
        logger.debug("Marked event %s processed", event_id)

    def insert_action_record(event_id: int, action_type: str, details: Dict[str, Any], timestamp: float):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO actions (event_id, action_type, details, timestamp) VALUES (?, ?, ?, ?)",
            (event_id, action_type, json.dumps(details), timestamp),
        )
        aid = cur.lastrowid
        conn.commit()
        conn.close()
        logger.debug("Inserted action id=%s for event %s", aid, event_id)
        return aid

    def fetch_recent_events(limit: int = 100):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, user, action, payload, timestamp, processed FROM events ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        out = []
        for r in rows:
            out.append({
                "id": r[0],
                "user": r[1],
                "action": r[2],
                "payload": json.loads(r[3]) if r[3] else None,
                "timestamp": r[4],
                "processed": r[5],
            })
        return out

    def fetch_recent_actions(limit: int = 100):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, event_id, action_type, details, timestamp FROM actions ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        out = []
        for r in rows:
            out.append({
                "id": r[0],
                "event_id": r[1],
                "action_type": r[2],
                "details": json.loads(r[3]) if r[3] else None,
                "timestamp": r[4],
            })
        return out

    def load_rules():
        if not os.path.isfile(RULES_FILE):
            default = {"score_threshold": SCORE_THRESHOLD}
            with open(RULES_FILE, "w") as f:
                json.dump(default, f, indent=2)
            return default
        with open(RULES_FILE, "r") as f:
            return json.load(f)

    def save_rules(rules: Dict[str, Any]):
        with open(RULES_FILE, "w") as f:
            json.dump(rules, f, indent=2)

    rules = load_rules()

    def score_event(event: Dict[str, Any]) -> float:
        action = event.get("action", "")
        payload = event.get("payload") or {}
        base = ACTION_BASE_SCORES.get(action, 0.2)
        boost = 0.0
        if isinstance(payload, dict):
            if "value" in payload and isinstance(payload["value"], (int, float)):
                boost += min(0.25, math.log1p(payload["value"]) / 10.0)
            if payload.get("priority") == "high":
                boost += 0.15
            if payload.get("suspected") is True:
                boost += 0.2
        freq_boost = 0.0
        occ = payload.get("occurrences") if isinstance(payload, dict) else None
        if isinstance(occ, int) and occ > 1:
            freq_boost += min(0.25, occ * 0.05)
        raw = base + boost + freq_boost
        score = max(0.0, min(1.0, raw))
        return score

    def should_trigger(score: float, event: Dict[str, Any]) -> bool:
        thr = float(rules.get("score_threshold", SCORE_THRESHOLD))
        return score >= thr

    def send_email_sync(subject: str, body: str, to_addr: str = ALERT_TO):
        if not SMTP_USER or not SMTP_PASSWORD:
            logger.error("SMTP config missing (SMTP_USER/SMTP_PASSWORD). Email not sent.")
            raise RuntimeError("SMTP_USER or SMTP_PASSWORD not configured in env")
        last_exc = None
        for attempt in range(1, MAX_EMAIL_RETRIES + 1):
            try:
                msg = EmailMessage()
                msg["Subject"] = subject
                msg["From"] = SMTP_FROM or SMTP_USER
                msg["To"] = to_addr
                msg.set_content(body)
                if SMTP_PORT == 465:
                    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
                        smtp.login(SMTP_USER, SMTP_PASSWORD)
                        smtp.send_message(msg)
                else:
                    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
                        smtp.ehlo()
                        smtp.starttls()
                        smtp.ehlo()
                        smtp.login(SMTP_USER, SMTP_PASSWORD)
                        smtp.send_message(msg)
                logger.info("Email sent to %s (subject=%s)", to_addr, subject)
                return True
            except Exception as e:
                last_exc = e
                logger.warning("Email send attempt %d failed: %s", attempt, str(e))
                time.sleep(EMAIL_RETRY_BACKOFF_SEC * attempt)
        logger.error("Failed to send email after %d tries: %s", MAX_EMAIL_RETRIES, str(last_exc))
        raise last_exc

    class ConnectionManager:
        def __init__(self):
            self.active: List[WebSocket] = []

        async def connect(self, websocket: WebSocket):
            await websocket.accept()
            self.active.append(websocket)

        def disconnect(self, websocket: WebSocket):
            try:
                self.active.remove(websocket)
            except ValueError:
                pass

        async def broadcast(self, message: Dict[str, Any]):
            data = json.dumps(message, default=str)
            to_remove = []
            for ws in list(self.active):
                try:
                    await ws.send_text(data)
                except Exception:
                    to_remove.append(ws)
            for r in to_remove:
                self.disconnect(r)

    manager = ConnectionManager()

    def execute_action_send_email(event: Dict[str, Any], score: float):
        subj = f"⚡ THE13TH Alert — {event.get('action')} (score={score:.2f})"
        ts = datetime.fromtimestamp(event.get("timestamp", time.time()), tz=timezone.utc).astimezone().isoformat()
        body = f"""THE13TH Admin Intelligence Alert

    Event ID: {event.get('id')}
    Action: {event.get('action')}
    User: {event.get('user')}
    Timestamp: {ts}
    Score: {score:.3f}

    Payload:
    {json.dumps(event.get('payload', {}), indent=2)}

    This message was auto-generated by THE13TH Admin Intelligence MVP.
    """
        try:
            send_email_sync(subj, body, ALERT_TO)
            details = {"status": "sent", "to": ALERT_TO, "score": score}
        except Exception as e:
            details = {"status": "failed", "error": str(e), "score": score}
            logger.exception("Email send failed for event %s", event.get("id"))
        insert_action_record(event["id"], "email_alert", details, time.time())
        asyncio.run(broadcast_nonblock({"type": "action", "payload": {"event_id": event["id"], "details": details}}))

    def broadcast_nonblock(message: Dict[str, Any]):
        async def _b():
            await manager.broadcast(message)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            asyncio.create_task(manager.broadcast(message))
        else:
            asyncio.run(_b())

    worker_started = False

    async def worker_loop():
        global worker_started
        if worker_started:
            return
        worker_started = True
        logger.info("Admin Intelligence worker started (poll interval %ss)", POLL_INTERVAL)
        while True:
            try:
                events = fetch_unprocessed_events(limit=50)
                if not events:
                    await asyncio.sleep(POLL_INTERVAL)
                    continue
                for ev in events:
                    try:
                        score = score_event(ev)
                    except Exception as e:
                        logger.exception("Scoring failed for event %s: %s", ev.get("id"), str(e))
                        mark_event_processed(ev["id"])
                        continue
                    if should_trigger(score, ev):
                        logger.info("Triggering action for event %s (action=%s score=%.3f)", ev["id"], ev["action"], score)
                        loop = asyncio.get_running_loop()
                        await loop.run_in_executor(None, execute_action_send_email, ev, score)
                    else:
                        logger.debug("No action for event %s (score=%.3f)", ev["id"], score)
                    mark_event_processed(ev["id"])
                    asyncio.create_task(manager.broadcast({"type": "event", "payload": ev}))
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.exception("Worker loop error: %s", str(e))
                await asyncio.sleep(max(5, POLL_INTERVAL))

    @app.on_event("startup")
    async def startup_event():
        init_db()
        global rules
        rules = load_rules()
        asyncio.create_task(worker_loop())

    class EventIn(BaseModel):
        user: Optional[str] = None
        action: str
        payload: Optional[Dict[str, Any]] = None
        timestamp: Optional[float] = None

    @app.post("/events", status_code=201)
    async def post_event(evt: EventIn):
        ts = evt.timestamp or time.time()
        eid = insert_event(evt.user, evt.action, evt.payload, ts)
        ev = {"id": eid, "user": evt.user, "action": evt.action, "payload": evt.payload, "timestamp": ts}
        asyncio.create_task(manager.broadcast({"type": "event", "payload": ev}))
        logger.info("Received event id=%s action=%s user=%s", eid, evt.action, evt.user)
        return {"status": "ok", "event_id": eid}

    @app.get("/admin/intel")
    async def admin_intel(limit: int = 100):
        events = fetch_recent_events(limit=limit)
        actions = fetch_recent_actions(limit=limit)
        return {"events": events, "actions": actions, "now": time.time(), "rules": rules}

    @app.get("/admin/rules")
    async def get_rules():
        return rules

    @app.put("/admin/rules")
    async def put_rules(payload: Dict[str, Any]):
        global rules
        rules = payload
        save_rules(rules)
        return {"status": "ok", "rules": rules}

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok", "ts": time.time()}

    @app.get("/intel")
    async def intel_index():
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.isfile(index_path):
            return FileResponse(index_path)
        return HTMLResponse("<html><body><h3>Dashboard not built. Run npm build under web/admin_ui/</h3></body></html>")

    @app.websocket("/intel/stream")
    async def websocket_endpoint(websocket: WebSocket):
        await manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(websocket)

    @app.get("/")
    async def root():
        return {"service": "THE13TH Admin Intelligence (Core 2.5)", "status": "running"}

    if __name__ == "__main__":
        import uvicorn
        uvicorn.run("main_admin_intel:app", host="0.0.0.0", port=8000, reload=True)
    ''')

    # rules.json
    write(os.path.join(ROOT, "rules.json"), r'''
    {
      "score_threshold": 0.8
    }
    ''')

    # frontend package.json
    write(os.path.join(WEB, "package.json"), r'''
    {
      "name": "the13th-admin-ui",
      "version": "0.1.0",
      "private": true,
      "scripts": {
        "dev": "vite",
        "build": "vite build",
        "preview": "vite preview"
      },
      "dependencies": {
        "react": "^18.2.0",
        "react-dom": "^18.2.0",
        "recharts": "^2.4.0"
      },
      "devDependencies": {
        "vite": "^5.0.0",
        "@vitejs/plugin-react": "^3.0.0"
      }
    }
    ''')

    # index.html
    write(os.path.join(WEB, "index.html"), r'''
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>THE13TH Intelligence Dashboard</title>
      </head>
      <body>
        <div id="root"></div>
        <script type="module" src="/src/main.jsx"></script>
      </body>
    </html>
    ''')

    # vite.config.js
    write(os.path.join(WEB, "vite.config.js"), r'''
    import { defineConfig } from 'vite'
    import react from '@vitejs/plugin-react'

    export default defineConfig({
      plugins: [react()],
      build: {
        outDir: 'dist'
      }
    })
    ''')

    # src/main.jsx
    write(os.path.join(SRC, "main.jsx"), r'''
    import React from 'react'
    import { createRoot } from 'react-dom/client'
    import App from './App'
    import './styles.css'

    createRoot(document.getElementById('root')).render(<App />)
    ''')

    # src/App.jsx
    write(os.path.join(SRC, "App.jsx"), r'''
    import React, { useEffect, useState, useRef } from 'react'
    import EventFeed from './components/EventFeed'
    import ScoreChart from './components/ScoreChart'
    import RulesEditor from './components/RulesEditor'
    import api from './api'

    export default function App(){
      const [events, setEvents] = useState([])
      const [actions, setActions] = useState([])
      const [rules, setRules] = useState({})
      const wsRef = useRef(null)

      useEffect(()=>{
        api.getIntel().then(data=>{
          setEvents(data.events)
          setActions(data.actions)
          setRules(data.rules || {score_threshold:0.8})
        })

        const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
        const wsUrl = `${proto}://${window.location.host}/intel/stream`
        const ws = new WebSocket(wsUrl)
        ws.onopen = ()=> console.log('WS open')
        ws.onmessage = (m)=>{
          try{
            const msg = JSON.parse(m.data)
            if(msg.type === 'event'){
              setEvents(prev=>[msg.payload, ...prev].slice(0,200))
            } else if(msg.type === 'action'){
              setActions(prev=>[msg.payload, ...prev].slice(0,200))
            }
          }catch(e){console.warn(e)}
        }
        ws.onclose = ()=> console.log('WS closed')
        wsRef.current = ws
        return ()=> ws.close()
      }, [])

      const onUpdateRules = async(newRules)=>{
        const res = await api.putRules(newRules)
        setRules(res.rules)
      }

      return (
        <div className="app-root">
          <header className="header">
            <h1>THE13TH Intelligence Dashboard</h1>
            <div className="status">Worker: <span>Online</span></div>
          </header>
          <main className="grid">
            <section className="left">
              <RulesEditor rules={rules} onSave={onUpdateRules} />
              <EventFeed events={events} />
            </section>
            <aside className="right">
              <ScoreChart events={events} />
              <div className="actions">
                <h3>Recent Actions</h3>
                <ul>
                  {actions.map((a, idx)=>(
                    <li key={idx}><strong>Event {a.payload?.event_id}</strong> — {a.payload?.details?.status}</li>
                  ))}
                </ul>
              </div>
            </aside>
          </main>
        </div>
      )
    }
    ''')

    # src/api.js
    write(os.path.join(SRC, "api.js"), r'''
    const base = '' // same origin
    export default {
      getIntel: async ()=>{
        const r = await fetch('/admin/intel')
        return r.json()
      },
      getRules: async ()=>{
        const r = await fetch('/admin/rules')
        return r.json()
      },
      putRules: async (rules)=>{
        const r = await fetch('/admin/rules', {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(rules)})
        return r.json()
      }
    }
    ''')

    # components/EventFeed.jsx
    write(os.path.join(COMP, "EventFeed.jsx"), r'''
    import React from 'react'
    export default function EventFeed({events}){
      return (
        <div className="events">
          <h3>Event Feed</h3>
          <ul>
            {events.map(ev=> (
              <li key={ev.id} className="event-row">
                <div><strong>{ev.action}</strong> — {ev.user}</div>
                <div className="meta">{new Date(ev.timestamp*1000).toLocaleString()}</div>
                <pre className="payload">{JSON.stringify(ev.payload||{},null,2)}</pre>
              </li>
            ))}
          </ul>
        </div>
      )
    }
    ''')

    # components/ScoreChart.jsx
    write(os.path.join(COMP, "ScoreChart.jsx"), r'''
    import React from 'react'
    import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

    export default function ScoreChart({events}){
      const data = events.slice(0,50).map(ev=>({
        t: new Date(ev.timestamp*1000).toLocaleTimeString(),
        score: (()=>{
          const map = {lead_hot:1, client_upgrade:1, billing_failure:0.85}
          return map[ev.action] ?? 0.2
        })()
      })).reverse()

      return (
        <div style={{height:240}}>
          <h3>Recent Scores</h3>
          <ResponsiveContainer>
            <LineChart data={data}>
              <XAxis dataKey="t" />
              <YAxis domain={[0,1]} />
              <Tooltip />
              <Line type="monotone" dataKey="score" stroke="#6b21a8" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )
    }
    ''')

    # components/RulesEditor.jsx
    write(os.path.join(COMP, "RulesEditor.jsx"), r'''
    import React, {useState, useEffect} from 'react'
    import api from '../api'

    export default function RulesEditor({rules, onSave}){
      const [local, setLocal] = useState(rules)
      useEffect(()=> setLocal(rules), [rules])
      const save = ()=>{
        onSave(local)
      }
      return (
        <div className="rules">
          <h3>Rules</h3>
          <div>
            <label>Score threshold: {local?.score_threshold}</label>
            <input type="range" min="0" max="1" step="0.01" value={local?.score_threshold||0.8}
              onChange={e=> setLocal({...local, score_threshold: parseFloat(e.target.value)})} />
            <button onClick={save}>Save Rules</button>
          </div>
          <pre>{JSON.stringify(local, null, 2)}</pre>
        </div>
      )
    }
    ''')

    # styles.css
    write(os.path.join(SRC, "styles.css"), r'''
    :root{--bg:#f4f4f6; --accent:#6b21a8; --muted:#666}
    body{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,"Helvetica Neue",Arial;margin:0;background:var(--bg);color:#111}
    .app-root{padding:18px}
    .header{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
    .grid{display:grid;grid-template-columns:1fr 360px;gap:12px}
    .left{padding:12px}
    .right{padding:12px;background:#fff;border-radius:8px}
    .events{background:#fff;padding:12px;border-radius:8px}
    .event-row{border-bottom:1px solid #eee;padding:8px}
    .payload{background:#fafafa;padding:6px;border-radius:4px;font-size:12px}
    .rules{background:#fff;padding:12px;border-radius:8px;margin-bottom:12px}
    h1{color:var(--accent)}
    ''')

    print("\nAll files created.")
    print("Next steps:")
    print("  1) cd saas_demo/web/admin_ui && npm install && npm run build")
    print("  2) set -a && source .env && set +a")
    print("  3) uvicorn main_admin_intel:app --reload")
    print("Then open: http://127.0.0.1:8000/intel\n")

if __name__ == "__main__":
    main()
