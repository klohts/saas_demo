#!/usr/bin/env python3
"""
Safe & idempotent admin hardening script
- Fixes auth_magic.py
- Patches main.py
- Ensures sessions DB schema
- Generates Dockerfile + .env.sample
- Prints ADMIN_PASSWORD_HASH for production
"""

import os, shutil, hashlib, hmac, sqlite3, secrets, time, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UTILS = ROOT / "utils"
AUTH_FILE = UTILS / "auth_magic.py"
MAIN_FILE = ROOT / "main.py"
DATA_DIR = ROOT / "data"
SESS_DB = DATA_DIR / "sessions.db"
BACKUP_DIR = ROOT / "setup_backups"
DOCKERFILE = ROOT / "Dockerfile"
ENV_SAMPLE = ROOT / ".env.sample"

DEFAULT_ADMIN_EMAIL = "admin@the13th.com"
DEFAULT_ADMIN_PASSWORD = "The13th@2025"
PBKDF2_ITER = 150_000
SALT = os.environ.get("ADMIN_PWD_SALT", "the13th-default-salt").encode()

def utc_now():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

def ensure_dirs():
    BACKUP_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UTILS.mkdir(parents=True, exist_ok=True)

def backup(path: Path):
    if not path.exists(): return
    dest = BACKUP_DIR / f"{path.name}.{utc_now()}.bak"
    shutil.copy2(path, dest)
    print(f"✅ Backup: {path.name} → {dest.name}")

def make_hash(pwd: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pwd.encode(), SALT, PBKDF2_ITER).hex()

# ─────────────────────────────────────────────────────────
# Write auth file
# ─────────────────────────────────────────────────────────
def write_auth_magic():
    backup(AUTH_FILE)
    AUTH_FILE.write_text(f"""# Auto-generated secure auth
import os, sqlite3, time, secrets, hashlib, hmac
from datetime import datetime, timezone, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = str(DATA_DIR / "sessions.db")

PBKDF2_ITER={PBKDF2_ITER}
SALT={repr(SALT.decode())}.encode()

def hash_pwd(p): return hashlib.pbkdf2_hmac("sha256", p.encode(), SALT, PBKDF2_ITER).hex()
def verify_pwd(p, h): return hmac.compare_digest(hash_pwd(p), h)

def get_admin_hash():
    return os.environ.get("ADMIN_PASSWORD_HASH") or hash_pwd(os.environ.get("ADMIN_PASSWORD","{DEFAULT_ADMIN_PASSWORD}"))

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
    return email.lower()==os.environ.get("ADMIN_EMAIL","{DEFAULT_ADMIN_EMAIL}").lower() and verify_pwd(pwd,get_admin_hash())

def create_session():
    t,se=secrets.token_urlsafe(32),datetime.now(timezone.utc)
    with sqlite3.connect(DB_PATH) as c:
        c.execute("INSERT OR REPLACE INTO sessions VALUES(?,?,?,?,?)",
        (t,os.environ.get("ADMIN_EMAIL","{DEFAULT_ADMIN_EMAIL}"),"admin",se.isoformat(),(se+timedelta(hours=6)).timestamp())); c.commit()
    log_audit(os.environ.get("ADMIN_EMAIL"),"login","created session")
    return t

def kill_session(t):
    with sqlite3.connect(DB_PATH) as c:
        c.execute("DELETE FROM sessions WHERE token=?", (t,)); c.commit()
    log_audit("admin","logout","session killed")
""")
    print("✅ Wrote auth_magic.py")



# ─────────────────────────────────────────────────────────
# Patch main.py safely WITHOUT regex disasters
# ─────────────────────────────────────────────────────────
def patch_main_py():
    backup(MAIN_FILE)
    src = MAIN_FILE.read_text()

    # 1. Add datetime to jinja if missing
    if "templates.env.globals" not in src:
        src = src.replace(
            "templates = Jinja2Templates(directory=\"templates\")",
            "templates = Jinja2Templates(directory=\"templates\")\ntemplates.env.globals['datetime'] = datetime\nCOOKIE_SECURE = os.environ.get('COOKIE_SECURE','0')=='1'"
        )

    # 2. Replace login handler (safe replace, no broken regex)
    if "async def admin_login_submit" in src:
        login_block = """
@app.post("/admin/login")
async def admin_login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    from utils.auth_magic import verify_admin, create_session, log_audit
    if verify_admin(email, password):
        t = create_session()
        r = RedirectResponse("/admin/tools", 303)
        r.set_cookie("session_token", t, httponly=True, max_age=21600, secure=COOKIE_SECURE, samesite="lax")
        log_audit(email,"login_ok",request.client.host if request.client else "?")
        return r
    log_audit(email,"login_fail",request.client.host if request.client else "?")
    return templates.TemplateResponse("admin_login.html", {"request":request,"error":"Invalid"}, status_code=401)
"""
        src = re.sub(r"async def admin_login_submit.*?return .*?\)", login_block, src, flags=re.S)

    # 3. Replace logout safely
    if "def admin_logout" in src:
        logout_block = """
@app.get("/admin/logout")
def admin_logout(request: Request):
    from utils.auth_magic import kill_session
    t = request.cookies.get("session_token")
    if t: kill_session(t)
    r = RedirectResponse("/admin/login",303)
    r.delete_cookie("session_token")
    return r
"""
        src = re.sub(r"def admin_logout.*?return .*?\)", logout_block, src, flags=re.S)

    MAIN_FILE.write_text(src)
    print("✅ Patched main.py safely")

# ─────────────────────────────────────────────────────────
# DB migration
# ─────────────────────────────────────────────────────────
def migrate_db():
    with sqlite3.connect(SESS_DB) as c:
        c.execute("CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, email TEXT, role TEXT, created_at TEXT, expires_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS audit_logs(id INTEGER PRIMARY KEY, ts TEXT, actor TEXT, event TEXT, details TEXT)")
        have=[x[1] for x in c.execute("PRAGMA table_info(sessions)")]
        for col in ["email","role","created_at","expires_at"]:
            if col not in have:
                try: c.execute(f"ALTER TABLE sessions ADD COLUMN {col} TEXT")
                except: pass
        c.commit()
    print("✅ DB migrated")

# ─────────────────────────────────────────────────────────
# Docker + env
# ─────────────────────────────────────────────────────────
def write_docker_env():
    if not DOCKERFILE.exists():
        DOCKERFILE.write_text("FROM python:3.12-slim\nWORKDIR /app\nCOPY . .\nRUN pip install -r requirements.txt\nCMD uvicorn main:app --host 0.0.0.0 --port 8000")
        print("✅ Dockerfile created")
    if not ENV_SAMPLE.exists():
        ENV_SAMPLE.write_text(f"ADMIN_EMAIL={DEFAULT_ADMIN_EMAIL}\nADMIN_PASSWORD={DEFAULT_ADMIN_PASSWORD}\nADMIN_PASSWORD_HASH=\nCOOKIE_SECURE=0\n")
        print("✅ .env.sample created")

def main():
    ensure_dirs()
    write_auth_magic()
    patch_main_py()
    migrate_db()
    write_docker_env()
    print("\n🔑 ADMIN_PASSWORD_HASH for production:\n", make_hash(DEFAULT_ADMIN_PASSWORD), "\n")

if __name__ == "__main__":
    main()
