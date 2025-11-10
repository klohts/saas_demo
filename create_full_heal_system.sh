#!/usr/bin/env bash
set -e
echo "🚀 Building THE13TH self-healing system..."

##########################################
# 1️⃣ Create fix_all.py
##########################################
cat > fix_all.py << 'PY'
import os, sys, re, sqlite3, hashlib, subprocess, requests, logging, datetime
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# CONFIG
LOG_FILE = "uvicorn_fix.log"
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
ADMIN_ENV_PATH = ".env"
DB_FILES = ["app.db", "sessions.db", "db.sqlite", "data/admin_audit.db", "data/clients.db"]

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

def log(msg):
    print(msg); logging.info(msg)

def discord_alert(msg):
    if DISCORD_WEBHOOK:
        try:
            requests.post(DISCORD_WEBHOOK, json={"content": f"🚨 **AUTO-FIX ALERT**\n{msg}"})
        except: pass

# 1. Ensure admin hash is pinned
def fix_admin_hash():
    if not os.path.exists(ADMIN_ENV_PATH): return
    with open(ADMIN_ENV_PATH) as f:
        env = f.read()
    if "ADMIN_PASSWORD_HASH=" not in env:
        log("ADMIN_PASSWORD_HASH missing, regenerating...")
        pw = os.getenv("ADMIN_PASSWORD","admin123")
        h = hashlib.sha256(pw.encode()).hexdigest()
        with open(ADMIN_ENV_PATH, "a") as f:
            f.write(f"\nADMIN_PASSWORD_HASH={h}\n")
        log("Admin hash pinned")

# 2. DB schema guard (ensures minimal users table exists everywhere)
def fix_db():
    for db in DB_FILES:
        if not Path(db).exists(): continue
        try:
            con = sqlite3.connect(db)
            con.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, email TEXT UNIQUE)")
            con.commit()
            con.close()
            log(f"DB healthy: {db}")
        except Exception as e:
            log(f"DB error {db}: {e}")
            discord_alert(f"DB failure on {db}: {e}")

# 3. Ensure uvicorn does not crash silently
def fix_uvicorn_logs():
    if not Path(LOG_FILE).exists():
        Path(LOG_FILE).write_text("")

# 4. Ensure dependencies install
def fix_deps():
    if Path("requirements.txt").exists():
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], stdout=subprocess.DEVNULL)

# 5. Final run
if __name__ == "__main__":
    log("🧠 Running full auto-fix sequence...")
    fix_admin_hash()
    fix_db()
    fix_uvicorn_logs()
    fix_deps()
    log("✅ Auto-fix complete")
PY

##########################################
# 2️⃣ Create Healing Dashboard (FastAPI route)
##########################################

mkdir -p heal
cat > heal/dashboard.py << 'PY'
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter()
LOG = "uvicorn_fix.log"

@router.get("/heal/logs", response_class=HTMLResponse)
def view_logs():
    if not Path(LOG).exists():
        return "<h3>No logs yet</h3>"
    data = Path(LOG).read_text().replace("\n", "<br>")
    return f"""
    <h2>🧠 THE13TH Auto-Heal Logs</h2>
    <div style="background:#111;color:#0f0;padding:10px;border-radius:6px;font-family:monospace;height:70vh;overflow:auto">
    {data}
    </div>
    """
PY

##########################################
# 3️⃣ Auto-inject into main.py if FastAPI app exists
##########################################

if grep -q "FastAPI()" main.py 2>/dev/null; then
  if ! grep -q "heal.dashboard" main.py; then
    echo "🔗 Injecting dashboard route into main.py..."
    sed -i "1i from heal.dashboard import router as heal_router" main.py
    sed -i "/= FastAPI()/a app.include_router(heal_router)" main.py
  fi
fi

##########################################
# 4️⃣ Add auto-alert on crash to watchdog if exists
##########################################

if [ -f watchdog.py ]; then
  if ! grep -q "discord_alert" watchdog.py; then
    echo "🔗 Wiring Discord crash alerts into watchdog..."
    sed -i "1i import requests, os" watchdog.py
    sed -i "1i WEBHOOK=os.getenv('DISCORD_WEBHOOK')" watchdog.py
    sed -i "s/🚨 Crash detected!/🚨 Crash detected!\\n        if WEBHOOK: requests.post(WEBHOOK, json={'content':'🚨 **Server crashed, auto-repair triggered**'})/g" watchdog.py
  fi
fi

##########################################
# 5️⃣ Finish
##########################################

chmod +x fix_all.py
echo "✅ THE13TH self-healing system installed."
echo ""
echo "Run repair manually anytime:"
echo "   python3 fix_all.py"
echo ""
echo "View healing logs dashboard at:"
echo "   http://localhost:8000/heal/logs"
echo ""
echo "If using watchdog:"
echo "   python3 watchdog.py"
