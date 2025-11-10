"""
main_admin_intel.py
Single-file Admin Intelligence MVP for THE13TH.
Run: uvicorn main_admin_intel:app --reload
"""

import os, time, math, json, asyncio, logging, sqlite3, smtplib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from email.message import EmailMessage

# ---------- CONFIG ----------
DB_PATH = os.environ.get("ADMIN_INTEL_DB", "admin_intel.db")
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "5"))
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER)
ALERT_TO = os.environ.get("ALERT_TO", "rhettlohts@gmail.com")
SCORE_THRESHOLD = float(os.environ.get("SCORE_THRESHOLD", "0.8"))
ACTION_BASE_SCORES = {
    "signup": 0.3, "login": 0.1, "password_reset": 0.25,
    "lead_hot": 0.95, "client_upgrade": 0.9,
    "billing_failure": 0.85, "suspicious_activity": 0.9,
    "api_error": 0.4, "high_value_action": 0.9,
}

# ---- EMAIL CONFIG ----

EMAIL_RETRY_BACKOFF_SEC = 2  # seconds between retry attempts
MAX_EMAIL_RETRIES = 3

# ---------- LOGGING ----------

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("admin_intel")

app = FastAPI(title="THE13TH — Admin Intelligence (MVP)")

# --- helper: ms timestamp for JS ---
def ms(ts):
    return int(ts * 1000)

# ---------- STATIC FRONTEND ----------
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")

# Serve ALL dist files (so index.html, manifest, etc are reachable)
app.mount("/static", StaticFiles(directory=FRONTEND_DIST), name="static")

# Specifically serve Vite asset folder where hashed CSS/JS live
app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

from fastapi.responses import FileResponse

# Serve Admin SPA
@app.get("/admin")
def serve_admin():
    with open(os.path.join(FRONTEND_DIST, "index.html"), "r") as f:
        html = f.read()
    # Force base href to root so assets resolve properly
    html = html.replace(
        "<head>",
        "<head><base href=\"/\">", 1
    )
    return HTMLResponse(html)


# Optional: serve frontend at root as well
@app.get("/")
def serve_root():
    return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

@app.get("/intel")
def serve_dashboard():
    return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))


# ---------- SCHEMA ----------
class EventIn(BaseModel):
    user: Optional[str] = None
    action: str
    payload: Optional[Dict[str, Any]] = None
    timestamp: Optional[float] = None

# ---------- DATABASE HELPERS ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        action TEXT NOT NULL,
        payload TEXT,
        timestamp REAL NOT NULL,
        processed INTEGER DEFAULT 0
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER,
        action_type TEXT,
        details TEXT,
        timestamp REAL NOT NULL
    )""")
    conn.commit()
    conn.close()
    logger.info("DB initialized at %s", DB_PATH)

def insert_event(u, a, p, t):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO events (user, action, payload, timestamp, processed) VALUES (?, ?, ?, ?, 0)",
        (u, a, json.dumps(p) if p is not None else None, t),
    )
    eid = cur.lastrowid
    conn.commit()
    conn.close()
    logger.debug("Inserted event id=%s action=%s user=%s", eid, a, u)
    return eid

def fetch_recent_events(L: int = 100):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user, action, payload, timestamp, processed FROM events ORDER BY timestamp DESC LIMIT ?",
        (L,),
    )
    rows = cur.fetchall()
    conn.close()
    out = []
    for r in rows:
        out.append({
            "id": r[0],
            "user": r[1],
            "action": r[2],
            "payload": json.loads(r[3]) if r[3] else None,
            # convert seconds -> ms for JS Date
            "timestamp": ms(r[4]) if r[4] else ms(time.time()),
            "processed": r[5]
        })
    return out

def fetch_unprocessed_events(L: int = 50):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, user, action, payload, timestamp FROM events WHERE processed = 0 ORDER BY timestamp ASC LIMIT ?", (L,))
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

# ---------- SCORER ----------
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
    score = max(0.0, min(1.0, base + boost))
    logger.debug("Scored event %s action=%s => %.3f", event.get("id"), action, score)
    return score

# ---------- EMAIL SENDER ----------
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_sync(subject: str, body: str, to_email: str):
    logger.info(f"📧 Email queue: sending to {to_email} | subject: {subject}")

    for attempt in range(1, MAX_EMAIL_RETRIES + 1):
        try:
            msg = MIMEMultipart()
            msg["From"] = SMTP_USER
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
                smtp.starttls()
                smtp.login(SMTP_USER, SMTP_PASSWORD)
                smtp.send_message(msg)

            log_email_delivery(event_id=None, to_email=to_email, subject=subject, status="sent")
            logger.info(f"✅ Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.warning(f"⚠️ Email send attempt {attempt} failed: {e}")

    log_email_delivery(event_id=None, to_email=to_email, subject=subject, status="failed", error=str(e))
    return False



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

# ---------- BACKGROUND WORKER ----------
async def worker():
    logger.info("Admin Intelligence worker started (poll interval %ss)", POLL_INTERVAL)
    while True:
        try:
            events = fetch_unprocessed_events(50)
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

                if score >= SCORE_THRESHOLD:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, execute_action_send_email, ev, score)

                mark_event_processed(ev["id"])

            # short yield
            await asyncio.sleep(0.01)
        except Exception as e:
            logger.exception("Worker loop error: %s", str(e))
            await asyncio.sleep(max(5, POLL_INTERVAL))

# ---------- STABLE WEBSOCKET (full) ----------
@app.websocket("/intel/stream")
# ---------- STABLE WEBSOCKET (full) ----------
@app.websocket("/intel/stream")
async def stream(ws: WebSocket):
    await ws.accept()
    logger.info("WS client connected")
    last_event_id = None
    ping_task = None

    async def keepalive_ping():
        try:
            while True:
                await asyncio.sleep(5)
                # lightweight ping message to keep the connection alive
                try:
                    await ws.send_json({"type": "ping", "ts": ms(time.time())})
                except Exception:
                    # if send fails, exit the ping task; main loop will handle closure
                    return
        except asyncio.CancelledError:
            return
        except Exception:
            # ignore other errors and exit ping task
            return

    try:
        ping_task = asyncio.create_task(keepalive_ping())

        while True:
            # get latest 10 events
            events = fetch_recent_events(10)
            newest_id = events[0]["id"] if events else 0
            has_new = newest_id != last_event_id
            last_event_id = newest_id

            # ensure timestamps exist (they should already be ms)
            for e in events:
                if not e.get("timestamp"):
                    e["timestamp"] = ms(time.time())

            payload = {
                "type": "snapshot",
                "events": events,
                "scores": [{"ts": e["timestamp"], "score": score_event(e)} for e in events],
                "new": has_new,
                "ts": ms(time.time())
            }

            try:
                await ws.send_json(payload)
            except Exception:
                # if send fails, break and let cleanup run
                break

            # fast loop when there's new data so UI sees it immediately, otherwise heartbeat interval
            await asyncio.sleep(1 if has_new else 6)

    except WebSocketDisconnect:
        logger.info("WS client disconnected normally")
    except Exception as e:
        logger.error("WS error: %s", e)
    finally:
        if ping_task:
            ping_task.cancel()
        try:
            await ws.close()
        except:
            pass
        logger.info("WS cleanup complete")
@app.post("/events", status_code=201)
async def post_event(evt: EventIn, background: BackgroundTasks = None):
    ts = evt.timestamp or time.time()
    eid = insert_event(evt.user, evt.action, evt.payload, ts)
    logger.info("Received event id=%s action=%s user=%s", eid, evt.action, evt.user)
    # Note: websocket loop will detect new events and send snapshot quickly.
    return {"status": "ok", "event_id": eid}

@app.get("/admin/intel")
async def admin_intel(limit: int = 100):
    return {"events": fetch_recent_events(limit), "actions": [], "now": ms(time.time())}

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "ts": ms(time.time())}

@app.get("/")
async def root():
    return {"service": "THE13TH Admin Intelligence (MVP)", "status": "running"}

# ---------- STARTUP ----------
@app.on_event("startup")
async def startup_event():
    init_db()
    asyncio.create_task(worker())

# ---------- RUN DIRECT ----------
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting THE13TH Admin Intelligence MVP (direct run)...")
    uvicorn.run("main_admin_intel:app", host="0.0.0.0", port=8000, reload=True)


# --- EMAIL LOGGING & QUEUE TABLES ---
def init_email_tables():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            to_email TEXT,
            subject TEXT,
            status TEXT,
            error TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS email_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            subject TEXT,
            body TEXT,
            to_email TEXT,
            attempts INTEGER DEFAULT 0,
            next_retry_at REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        db.commit()

def log_email_delivery(event_id, to_email, subject, status, error=None):
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            "INSERT INTO email_logs(event_id, to_email, subject, status, error) VALUES (?,?,?,?,?)",
            (event_id, to_email, subject, status, error)
        )
        db.commit()

def enqueue_email(event_id, subject, body, to_email):
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            "INSERT INTO email_queue(event_id, subject, body, to_email) VALUES (?,?,?,?)",
            (event_id, subject, body, to_email)
        )
        db.commit()

async def process_email_queue():
    while True:
        await asyncio.sleep(10)
        now = time.time()
        with sqlite3.connect(DB_PATH) as db:
            rows = db.execute(
                "SELECT id,event_id,subject,body,to_email,attempts FROM email_queue WHERE next_retry_at < ?",
                (now,),
            ).fetchall()

        for qid,event_id,subject,body,to_email,attempts in rows:
            ok = send_email_sync(subject, body, to_email)
            with sqlite3.connect(DB_PATH) as db:
                if ok:
                    db.execute("DELETE FROM email_queue WHERE id=?", (qid,))
                else:
                    db.execute(
                        "UPDATE email_queue SET attempts=attempts+1, next_retry_at=? WHERE id=?",
                        (time.time() + (2 ** (attempts + 1)), qid)
                    )
                db.commit()


@app.post("/test-email")
def test_email_endpoint(payload: dict):
    subject = payload.get("subject", "🔥 Test Email")
    body = payload.get("body", "This is a test email from THE13TH admin system.")
    to = payload.get("to", ALERT_TO)
    ok = send_email_sync(subject, body, to)
    return {"status": "sent" if ok else "failed"}

@app.on_event("startup")
async def __patch_startup():
    init_email_tables()
    asyncio.create_task(process_email_queue())

# ================= ADMIN DASHBOARD API INJECTED =================

from fastapi import Body

# Track socket stats
SOCKET_STATS = {
    "connected_clients": 0,
    "last_message_ts": None,
    "total_sent": 0
}

# Track connected sockets count
@app.websocket("/intel/stream")
async def track_socket(websocket):
    global SOCKET_STATS
    await websocket.accept()
    SOCKET_STATS["connected_clients"] += 1
    try:
        while True:
            data = await websocket.receive_text()
            SOCKET_STATS["last_message_ts"] = datetime.utcnow().isoformat()
            SOCKET_STATS["total_sent"] += 1
            await websocket.send_text(data)
    except:
        pass
    finally:
        SOCKET_STATS["connected_clients"] -= 1

@app.get("/admin/api/socket_stats")
def api_socket_stats():
    return SOCKET_STATS

@app.get("/admin/api/email_queue")
def api_email_queue():
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM email_queue ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

@app.post("/admin/api/email_queue/{qid}/retry")
def api_email_retry(qid: int):
    with sqlite3.connect(DB_PATH) as db:
        row = db.execute("SELECT * FROM email_queue WHERE id=?", (qid,)).fetchone()
        if not row:
            return {"status":"not_found"}
        enqueue_email(row[1], row[2], row[3], row[4])
        return {"status":"requeued"}

@app.delete("/admin/api/email_queue/{qid}")
def api_email_delete(qid: int):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("DELETE FROM email_queue WHERE id=?", (qid,))
        db.commit()
    return {"status":"deleted"}

@app.get("/admin/api/email_logs")
def api_email_logs(limit: int = 200):
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT * FROM email_logs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

# ==============================================================


# {SCRIPT_MARKER}
# DO NOT EDIT THIS BLOCK MANUALLY — generated by scripts/wire_everything_admin.py
import sqlite3
import asyncio
from fastapi import HTTPException

# Determine DB_PATH used by the app (fallback to admin_intel.db)
try:
    DB_PATH  # if defined earlier in file
except NameError:
    DB_PATH = os.path.join(os.path.dirname(__file__), "admin_intel.db")

# Ensure tables for email logs / queue
def init_email_tables():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            to_email TEXT,
            subject TEXT,
            status TEXT,
            error TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS email_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            subject TEXT,
            body TEXT,
            to_email TEXT,
            attempts INTEGER DEFAULT 0,
            next_retry_at REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        db.commit()

def log_email_delivery(event_id, to_email, subject, status, error=None):
    try:
        with sqlite3.connect(DB_PATH) as db:
            db.execute(
                "INSERT INTO email_logs(event_id, to_email, subject, status, error) VALUES (?,?,?,?,?)",
                (event_id, to_email, subject, status, error)
            )
            db.commit()
    except Exception as e:
        logger.exception("Failed to log email delivery: %s", e)

def enqueue_email(event_id, subject, body, to_email):
    try:
        with sqlite3.connect(DB_PATH) as db:
            db.execute(
                "INSERT INTO email_queue(event_id, subject, body, to_email, next_retry_at) VALUES (?,?,?,?,?)",
                (event_id, subject, body, to_email, 0)
            )
            db.commit()
    except Exception as e:
        logger.exception("Failed to enqueue email: %s", e)

# Simple queue processor (async background task)
async def process_email_queue_worker():
    print("Email queue worker started")
    while True:
        try:
            now = time.time()
            with sqlite3.connect(DB_PATH) as db:
                rows = db.execute(
                    "SELECT id,event_id,subject,body,to_email,attempts FROM email_queue WHERE next_retry_at <= ? ORDER BY id ASC LIMIT 10",
                    (now,)
                ).fetchall()

            for row in rows:
                qid = row[0]
                event_id = row[1]
                subject = row[2]
                body = row[3]
                to_email = row[4]
                attempts = row[5] or 0

                ok = False
                try:
                    ok = send_email_sync(subject, body, to_email)
                except Exception as e:
                    logger.exception("send_email_sync raised: %s", e)

                with sqlite3.connect(DB_PATH) as db:
                    if ok:
                        db.execute("DELETE FROM email_queue WHERE id=?", (qid,))
                        log_email_delivery(event_id, to_email, subject, "sent", None)
                    else:
                        attempts += 1
                        backoff = (2 ** attempts) + 1
                        db.execute("UPDATE email_queue SET attempts=?, next_retry_at=? WHERE id=?", (attempts, time.time() + backoff, qid))
                        log_email_delivery(event_id, to_email, subject, "failed", "queued for retry")
                    db.commit()
        except Exception as e:
            logger.exception("Email queue worker error: %s", e)
        await asyncio.sleep(5)

# Socket stats collector
SOCKET_STATS = {"connected_clients": 0, "last_message_ts": None, "total_sent": 0}

# Expose endpoints the AdminDashboard expects
@app.get("/admin/api/socket_stats")
def api_socket_stats():
    return SOCKET_STATS

@app.get("/admin/api/email_queue")
def api_email_queue():
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM email_queue ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

@app.post("/admin/api/email_queue/{qid}/retry")
def api_email_retry(qid: int):
    with sqlite3.connect(DB_PATH) as db:
        row = db.execute("SELECT id,event_id,subject,body,to_email FROM email_queue WHERE id=?", (qid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="not found")
        # simply set next_retry_at to now to retry immediately
        db.execute("UPDATE email_queue SET next_retry_at=?, attempts=0 WHERE id=?", (0, qid))
        db.commit()
        return {"status":"requeued"}

@app.delete("/admin/api/email_queue/{qid}")
def api_email_delete(qid: int):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("DELETE FROM email_queue WHERE id=?", (qid,))
        db.commit()
    return {"status":"deleted"}

@app.get("/admin/api/email_logs")
def api_email_logs(limit: int = 200):
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM email_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

# Serve the built frontend (production) at /admin
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")

try:
    # Mount static files folder for assets
    if not any(m.name == "frontend_dist" for m in app.router.routes if hasattr(m, "name")):
        app.mount("/admin/static", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="frontend_dist")
except Exception:
    # ignore mount errors if already mounted
    pass

@app.get("/admin")
@app.get("/admin/{catchall:path}")
def serve_admin(catchall: str = ""):
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend not built. Run `npm run build` in /frontend first."}

# Ensure initialization at startup
@app.on_event("startup")
async def _admin_dashboard_startup():
    try:
        init_email_tables()
    except Exception as e:
        logger.exception("init_email_tables failed: %s", e)
    # start background queue worker only once
    try:
        asyncio.create_task(process_email_queue_worker())
    except Exception as e:
        logger.exception("Failed to start email queue worker: %s", e)

# end injected block


# {SCRIPT_MARKER}
# DO NOT EDIT THIS BLOCK MANUALLY — generated by scripts/wire_everything_admin.py
import sqlite3
import asyncio
from fastapi import HTTPException

# Determine DB_PATH used by the app (fallback to admin_intel.db)
try:
    DB_PATH  # if defined earlier in file
except NameError:
    DB_PATH = os.path.join(os.path.dirname(__file__), "admin_intel.db")

# Ensure tables for email logs / queue
def init_email_tables():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            to_email TEXT,
            subject TEXT,
            status TEXT,
            error TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS email_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            subject TEXT,
            body TEXT,
            to_email TEXT,
            attempts INTEGER DEFAULT 0,
            next_retry_at REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        db.commit()

def log_email_delivery(event_id, to_email, subject, status, error=None):
    try:
        with sqlite3.connect(DB_PATH) as db:
            db.execute(
                "INSERT INTO email_logs(event_id, to_email, subject, status, error) VALUES (?,?,?,?,?)",
                (event_id, to_email, subject, status, error)
            )
            db.commit()
    except Exception as e:
        logger.exception("Failed to log email delivery: %s", e)

def enqueue_email(event_id, subject, body, to_email):
    try:
        with sqlite3.connect(DB_PATH) as db:
            db.execute(
                "INSERT INTO email_queue(event_id, subject, body, to_email, next_retry_at) VALUES (?,?,?,?,?)",
                (event_id, subject, body, to_email, 0)
            )
            db.commit()
    except Exception as e:
        logger.exception("Failed to enqueue email: %s", e)

# Simple queue processor (async background task)
async def process_email_queue_worker():
    print("Email queue worker started")
    while True:
        try:
            now = time.time()
            with sqlite3.connect(DB_PATH) as db:
                rows = db.execute(
                    "SELECT id,event_id,subject,body,to_email,attempts FROM email_queue WHERE next_retry_at <= ? ORDER BY id ASC LIMIT 10",
                    (now,)
                ).fetchall()

            for row in rows:
                qid = row[0]
                event_id = row[1]
                subject = row[2]
                body = row[3]
                to_email = row[4]
                attempts = row[5] or 0

                ok = False
                try:
                    ok = send_email_sync(subject, body, to_email)
                except Exception as e:
                    logger.exception("send_email_sync raised: %s", e)

                with sqlite3.connect(DB_PATH) as db:
                    if ok:
                        db.execute("DELETE FROM email_queue WHERE id=?", (qid,))
                        log_email_delivery(event_id, to_email, subject, "sent", None)
                    else:
                        attempts += 1
                        backoff = (2 ** attempts) + 1
                        db.execute("UPDATE email_queue SET attempts=?, next_retry_at=? WHERE id=?", (attempts, time.time() + backoff, qid))
                        log_email_delivery(event_id, to_email, subject, "failed", "queued for retry")
                    db.commit()
        except Exception as e:
            logger.exception("Email queue worker error: %s", e)
        await asyncio.sleep(5)

# Socket stats collector
SOCKET_STATS = {"connected_clients": 0, "last_message_ts": None, "total_sent": 0}

# Expose endpoints the AdminDashboard expects
@app.get("/admin/api/socket_stats")
def api_socket_stats():
    return SOCKET_STATS

@app.get("/admin/api/email_queue")
def api_email_queue():
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM email_queue ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

@app.post("/admin/api/email_queue/{qid}/retry")
def api_email_retry(qid: int):
    with sqlite3.connect(DB_PATH) as db:
        row = db.execute("SELECT id,event_id,subject,body,to_email FROM email_queue WHERE id=?", (qid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="not found")
        # simply set next_retry_at to now to retry immediately
        db.execute("UPDATE email_queue SET next_retry_at=?, attempts=0 WHERE id=?", (0, qid))
        db.commit()
        return {"status":"requeued"}

@app.delete("/admin/api/email_queue/{qid}")
def api_email_delete(qid: int):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("DELETE FROM email_queue WHERE id=?", (qid,))
        db.commit()
    return {"status":"deleted"}

@app.get("/admin/api/email_logs")
def api_email_logs(limit: int = 200):
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM email_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

# Serve the built frontend (production) at /admin
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")

try:
    # Mount static files folder for assets
    if not any(m.name == "frontend_dist" for m in app.router.routes if hasattr(m, "name")):
        app.mount("/admin/static", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="frontend_dist")
except Exception:
    # ignore mount errors if already mounted
    pass

@app.get("/admin")
@app.get("/admin/{catchall:path}")
def serve_admin(catchall: str = ""):
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend not built. Run `npm run build` in /frontend first."}

# Ensure initialization at startup
@app.on_event("startup")
async def _admin_dashboard_startup():
    try:
        init_email_tables()
    except Exception as e:
        logger.exception("init_email_tables failed: %s", e)
    # start background queue worker only once
    try:
        asyncio.create_task(process_email_queue_worker())
    except Exception as e:
        logger.exception("Failed to start email queue worker: %s", e)

# end injected block


# {SCRIPT_MARKER}
# DO NOT EDIT THIS BLOCK MANUALLY — generated by scripts/wire_everything_admin.py
import sqlite3
import asyncio
from fastapi import HTTPException

# Determine DB_PATH used by the app (fallback to admin_intel.db)
try:
    DB_PATH  # if defined earlier in file
except NameError:
    DB_PATH = os.path.join(os.path.dirname(__file__), "admin_intel.db")

# Ensure tables for email logs / queue
def init_email_tables():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            to_email TEXT,
            subject TEXT,
            status TEXT,
            error TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS email_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            subject TEXT,
            body TEXT,
            to_email TEXT,
            attempts INTEGER DEFAULT 0,
            next_retry_at REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        db.commit()

def log_email_delivery(event_id, to_email, subject, status, error=None):
    try:
        with sqlite3.connect(DB_PATH) as db:
            db.execute(
                "INSERT INTO email_logs(event_id, to_email, subject, status, error) VALUES (?,?,?,?,?)",
                (event_id, to_email, subject, status, error)
            )
            db.commit()
    except Exception as e:
        logger.exception("Failed to log email delivery: %s", e)

def enqueue_email(event_id, subject, body, to_email):
    try:
        with sqlite3.connect(DB_PATH) as db:
            db.execute(
                "INSERT INTO email_queue(event_id, subject, body, to_email, next_retry_at) VALUES (?,?,?,?,?)",
                (event_id, subject, body, to_email, 0)
            )
            db.commit()
    except Exception as e:
        logger.exception("Failed to enqueue email: %s", e)

# Simple queue processor (async background task)
async def process_email_queue_worker():
    print("Email queue worker started")
    while True:
        try:
            now = time.time()
            with sqlite3.connect(DB_PATH) as db:
                rows = db.execute(
                    "SELECT id,event_id,subject,body,to_email,attempts FROM email_queue WHERE next_retry_at <= ? ORDER BY id ASC LIMIT 10",
                    (now,)
                ).fetchall()

            for row in rows:
                qid = row[0]
                event_id = row[1]
                subject = row[2]
                body = row[3]
                to_email = row[4]
                attempts = row[5] or 0

                ok = False
                try:
                    ok = send_email_sync(subject, body, to_email)
                except Exception as e:
                    logger.exception("send_email_sync raised: %s", e)

                with sqlite3.connect(DB_PATH) as db:
                    if ok:
                        db.execute("DELETE FROM email_queue WHERE id=?", (qid,))
                        log_email_delivery(event_id, to_email, subject, "sent", None)
                    else:
                        attempts += 1
                        backoff = (2 ** attempts) + 1
                        db.execute("UPDATE email_queue SET attempts=?, next_retry_at=? WHERE id=?", (attempts, time.time() + backoff, qid))
                        log_email_delivery(event_id, to_email, subject, "failed", "queued for retry")
                    db.commit()
        except Exception as e:
            logger.exception("Email queue worker error: %s", e)
        await asyncio.sleep(5)

# Socket stats collector
SOCKET_STATS = {"connected_clients": 0, "last_message_ts": None, "total_sent": 0}

# Expose endpoints the AdminDashboard expects
@app.get("/admin/api/socket_stats")
def api_socket_stats():
    return SOCKET_STATS

@app.get("/admin/api/email_queue")
def api_email_queue():
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM email_queue ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

@app.post("/admin/api/email_queue/{qid}/retry")
def api_email_retry(qid: int):
    with sqlite3.connect(DB_PATH) as db:
        row = db.execute("SELECT id,event_id,subject,body,to_email FROM email_queue WHERE id=?", (qid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="not found")
        # simply set next_retry_at to now to retry immediately
        db.execute("UPDATE email_queue SET next_retry_at=?, attempts=0 WHERE id=?", (0, qid))
        db.commit()
        return {"status":"requeued"}

@app.delete("/admin/api/email_queue/{qid}")
def api_email_delete(qid: int):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("DELETE FROM email_queue WHERE id=?", (qid,))
        db.commit()
    return {"status":"deleted"}

@app.get("/admin/api/email_logs")
def api_email_logs(limit: int = 200):
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM email_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

# Serve the built frontend (production) at /admin
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")

try:
    # Mount static files folder for assets
    if not any(m.name == "frontend_dist" for m in app.router.routes if hasattr(m, "name")):
        app.mount("/admin/static", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="frontend_dist")
except Exception:
    # ignore mount errors if already mounted
    pass

@app.get("/admin")
@app.get("/admin/{catchall:path}")
def serve_admin(catchall: str = ""):
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend not built. Run `npm run build` in /frontend first."}

# Ensure initialization at startup
@app.on_event("startup")
async def _admin_dashboard_startup():
    try:
        init_email_tables()
    except Exception as e:
        logger.exception("init_email_tables failed: %s", e)
    # start background queue worker only once
    try:
        asyncio.create_task(process_email_queue_worker())
    except Exception as e:
        logger.exception("Failed to start email queue worker: %s", e)

# end injected block
