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
