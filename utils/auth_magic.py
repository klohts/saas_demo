import secrets, sqlite3, time, os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "sessions.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS sessions (
        email TEXT, token TEXT, expires_at REAL
    )""")
    conn.commit(); conn.close()

def create_magic_link(email: str) -> str:
    """Generate and store a one-time token for email login."""
    token = secrets.token_urlsafe(24)
    expires_at = time.time() + 900   # 15 min valid
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO sessions VALUES (?, ?, ?)", (email, token, expires_at))
    conn.commit(); conn.close()
    return f"https://the13th.onrender.com/client/login?token={token}"

def validate_token(token: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT email, expires_at FROM sessions WHERE token=?", (token,))
    row = c.fetchone()
    conn.close()
    if not row: return None
    email, exp = row
    if time.time() > exp: return None
    return email

import requests

def notify_webhook(status: str, recipient: str, message: str = ""):
    """Notify configured Slack or Discord webhook on email delivery status."""
    url = os.getenv("WEBHOOK_URL")
    if not url:
        return
    payload = {
        "content": f"📡 **THE13TH Email {status.upper()}** → {recipient}\n{message}"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Webhook notification failed: {e}")

# Integrate webhook calls into existing log_email_delivery
def log_email_delivery(recipient: str, status: str, message: str = ""):
    from datetime import datetime
    import os
    log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "email_delivery.log")
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {status.upper()} — {recipient} — {message}\\n"
    with open(log_path, "a") as f:
        f.write(line)
    notify_webhook(status, recipient, message)
