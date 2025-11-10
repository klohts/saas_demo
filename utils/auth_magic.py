# Auto-generated secure auth
import os, sqlite3, time, secrets, hashlib, hmac
from datetime import datetime, timezone, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = str(DATA_DIR / "sessions.db")

PBKDF2_ITER=150000
SALT='the13th-default-salt'.encode()

def hash_pwd(p): return hashlib.pbkdf2_hmac("sha256", p.encode(), SALT, PBKDF2_ITER).hex()
def verify_pwd(p, h): return hmac.compare_digest(hash_pwd(p), h)

def get_admin_hash():
    return os.environ.get("ADMIN_PASSWORD_HASH") or hash_pwd(os.environ.get("ADMIN_PASSWORD","The13th@2025"))

def init_db():
    with sqlite3.connect(DB_PATH) as c:
        # Ensure tables exist
        c.execute("CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, email TEXT, role TEXT, created_at TEXT, expires_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS audit_logs(id INTEGER PRIMARY KEY, ts TEXT, actor TEXT, event TEXT, details TEXT)")

        # Ensure columns exist (safe migration)
        try: c.execute("ALTER TABLE sessions ADD COLUMN email TEXT")
        except: pass
        try: c.execute("ALTER TABLE sessions ADD COLUMN role TEXT")
        except: pass
        try: c.execute("ALTER TABLE sessions ADD COLUMN created_at TEXT")
        except: pass
        try: c.execute("ALTER TABLE sessions ADD COLUMN expires_at TEXT")
        except: pass

        c.commit()

init_db()

def log_audit(actor,event,details=""):
    with sqlite3.connect(DB_PATH) as c:
        c.execute("INSERT INTO audit_logs(ts,actor,event,details) VALUES(?,?,?,?)",
        (datetime.now(timezone.utc).isoformat(),actor,event,details)); c.commit()

def verify_admin(email,pwd):
    return email.lower()==os.environ.get("ADMIN_EMAIL","admin@the13th.com").lower() and verify_pwd(pwd,get_admin_hash())

def create_session():
    t,se=secrets.token_urlsafe(32),datetime.now(timezone.utc)
    with sqlite3.connect(DB_PATH) as c:
        c.execute("INSERT OR REPLACE INTO sessions VALUES(?,?,?,?,?)",
        (t,os.environ.get("ADMIN_EMAIL","admin@the13th.com"),"admin",se.isoformat(),(se+timedelta(hours=6)).timestamp())); c.commit()
    log_audit(os.environ.get("ADMIN_EMAIL"),"login","created session")
    return t

def kill_session(t):
    with sqlite3.connect(DB_PATH) as c:
        c.execute("DELETE FROM sessions WHERE token=?", (t,)); c.commit()
    log_audit("admin","logout","session killed")

def verify_admin_credentials(password: str) -> bool:
    import os, hashlib
    expected = os.getenv("ADMIN_PASSWORD_HASH")
    if not expected:
        return False
    return hashlib.sha256(password.encode()).hexdigest() == expected

def create_admin_session():
    import os, sqlite3, secrets
    from datetime import datetime, timedelta
    token = secrets.token_urlsafe(32)
    db = os.path.join(os.path.dirname(__file__), "..", "sessions.db")
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        email TEXT,
        role TEXT,
        created_at TEXT,
        expires_at TEXT
    )""")
    now = datetime.utcnow()
    exp = now + timedelta(hours=6)
    c.execute("INSERT OR REPLACE INTO sessions VALUES (?,?,?,?,?)",
              (token, "admin@the13th.ai", "admin", now.isoformat(), exp.isoformat()))
    conn.commit(); conn.close()
    return token


from fastapi import Request, HTTPException

async def auth_admin(request: Request):
    """
    Simple admin guard using session cookie or Authorization header
    """
    import sqlite3, os
    token = request.cookies.get("admin_session") or request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db = os.path.join(os.path.dirname(__file__), "..", "sessions.db")
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("SELECT role, expires_at FROM sessions WHERE token = ?", (token,))
    row = c.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid session")

    role, expires = row
    from datetime import datetime
    if role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    if datetime.fromisoformat(expires) < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Session expired")
    return True


def get_session(token: str):
    import os, sqlite3
    db = os.path.join(os.path.dirname(__file__), "..", "sessions.db")
    con = sqlite3.connect(db)
    row = con.execute("SELECT token, email, role, created_at, expires_at FROM sessions WHERE token=?",(token,)).fetchone()
    con.close()
    if not row:
        return None
    return {"token": row[0], "email": row[1], "role": row[2], "created_at": row[3], "expires_at": row[4]}
