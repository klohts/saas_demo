import re, sys, os

TARGET = "main_admin_intel.py"

if not os.path.exists(TARGET):
    print(f"❌ {TARGET} not found. Run this from the saas_demo/ directory.")
    sys.exit(1)

code = open(TARGET, "r", encoding="utf-8").read()

# 1. Ensure required config constants exist
config_block = """
# --- AUTO PATCHED CONFIG ---
EMAIL_RETRY_BACKOFF_SEC = 2
MAX_EMAIL_RETRIES = 3
"""

if "EMAIL_RETRY_BACKOFF_SEC" not in code:
    code = config_block + "\n" + code

# 2. Replace send_email_sync with UTF-8 + MIME safe version
email_func = r"def send_email_sync\(.*?return False"
replacement = """
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
"""
code = re.sub(email_func, replacement, code, flags=re.DOTALL)

# 3. Add DB tables for logging + persistent queue
injected_db = """
# --- EMAIL LOGGING & QUEUE TABLES ---
def init_email_tables():
    with sqlite3.connect(DB_PATH) as db:
        db.execute(\"\"\"CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            to_email TEXT,
            subject TEXT,
            status TEXT,
            error TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )\"\"\")
        db.execute(\"\"\"CREATE TABLE IF NOT EXISTS email_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            subject TEXT,
            body TEXT,
            to_email TEXT,
            attempts INTEGER DEFAULT 0,
            next_retry_at REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )\"\"\")
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
"""

if "init_email_tables" not in code:
    code += "\n" + injected_db

# 4. Add test-email endpoint
test_endpoint = """
@app.post("/test-email")
def test_email_endpoint(payload: dict):
    subject = payload.get("subject", "🔥 Test Email")
    body = payload.get("body", "This is a test email from THE13TH admin system.")
    to = payload.get("to", ALERT_TO)
    ok = send_email_sync(subject, body, to)
    return {"status": "sent" if ok else "failed"}
"""

if "/test-email" not in code:
    code += "\n" + test_endpoint

# 5. Wrap websocket broadcast safely
code = code.replace(
    "await ws.send_json(",
    "try:\n        await ws.send_json("
).replace(
    "await ws.send_json(",
    "        await ws.send_json(", 1
).replace(
    ")", ")\n    except RuntimeError:\n        logger.warning('Skipping dead websocket')", 1
)

# 6. Ensure tables and workers start on boot
startup_inject = """
@app.on_event("startup")
async def __patch_startup():
    init_email_tables()
    asyncio.create_task(process_email_queue())
"""

if "__patch_startup" not in code:
    code += startup_inject

# Write updated file
with open(TARGET, "w", encoding="utf-8") as f:
    f.write(code)

print("✅ main_admin_intel.py fully patched!")
print("Now restart Uvicorn.")
