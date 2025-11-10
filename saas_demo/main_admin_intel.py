# main_admin_intel.py

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


# ---------- SERVE REACT FRONTEND (VITE BUILD) ----------
from fastapi.responses import FileResponse

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")

# ✅ Serve compiled assets (JS/CSS)
app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

# ✅ Serve SPA for all frontend routes
@app.get("/admin/{full_path:path}")
@app.get("/admin")
@app.get("/intel")
@app.get("/")
def serve_react(full_path: str = ""):
    return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

