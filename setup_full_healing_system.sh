#!/usr/bin/env bash
set -e
echo "🩺 Setting up THE13TH full self-healing infrastructure..."

##########################################
# 1️⃣ fix_all.py — core auto-repair engine
##########################################
cat > fix_all.py << 'PY'
import os, sys, re, sqlite3, hashlib, subprocess, requests, logging
from pathlib import Path

LOG_FILE = "uvicorn_fix.log"
ADMIN_ENV_PATH = ".env"
DB_FILES = ["data/sessions.db", "data/app.db", "data/admin_audit.db", "sessions.db", "app.db", "db.sqlite"]
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

def log(msg):
    print(msg)
    logging.info(msg)

def discord_alert(msg):
    if DISCORD_WEBHOOK:
        try:
            requests.post(DISCORD_WEBHOOK, json={"content": f"🚨 **THE13TH AUTO-HEAL ALERT**\n{msg}"})
        except Exception as e:
            print("Discord alert failed:", e)

def fix_admin_hash():
    if not Path(ADMIN_ENV_PATH).exists(): return
    txt = Path(ADMIN_ENV_PATH).read_text()
    if "ADMIN_PASSWORD_HASH=" not in txt:
        pw = os.getenv("ADMIN_PASSWORD","th13_superpass")
        h = hashlib.sha256(pw.encode()).hexdigest()
        Path(ADMIN_ENV_PATH).write_text(txt + f"\nADMIN_PASSWORD_HASH={h}\n")
        log("🔐 Pinned missing ADMIN_PASSWORD_HASH")
    else:
        log("✅ ADMIN_PASSWORD_HASH already set")

def fix_databases():
    for db in DB_FILES:
        if not Path(db).exists(): continue
        try:
            con = sqlite3.connect(db)
            cur = con.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, email TEXT, role TEXT, created_at TEXT, expires_at REAL, twofa_code TEXT, twofa_expires REAL)")
            con.commit(); con.close()
            log(f"✅ DB ready: {db}")
        except Exception as e:
            log(f"❌ DB repair failed for {db}: {e}")
            discord_alert(f"DB repair failed for {db}: {e}")

def fix_dependencies():
    if Path("requirements.txt").exists():
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], stdout=subprocess.DEVNULL)
        log("📦 Dependencies checked")

def fix_email_utf8():
    f = "main.py"
    if not Path(f).exists(): return
    c = Path(f).read_text()
    if 'message.encode("utf-8")' not in c:
        c = re.sub(r"s\.sendmail\(SMTP_FROM, \[to_address\], message\)", 's.sendmail(SMTP_FROM, [to_address], message.encode("utf-8"))', c)
        Path(f).write_text(c)
        log("✉️ Patched UTF-8 email send in main.py")

def main():
    log("🧠 Running THE13TH auto-heal engine...")
    fix_admin_hash()
    fix_databases()
    fix_dependencies()
    fix_email_utf8()
    log("✅ All fixes applied successfully")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        discord_alert(f"Auto-heal failed: {e}")
        raise
PY

##########################################
# 2️⃣ heal dashboard
##########################################
mkdir -p heal
cat > heal/dashboard.py << 'PY'
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter()
LOG_FILE = "uvicorn_fix.log"

@router.get("/heal/logs", response_class=HTMLResponse)
def view_heal_logs():
    data = Path(LOG_FILE).read_text() if Path(LOG_FILE).exists() else "No logs yet"
    data = data.replace("\n", "<br>")
    return f"""
    <html><head><title>THE13TH Logs</title></head>
    <body style='background:#111;color:#0f0;font-family:monospace;padding:20px;'>
    <h2>🧠 THE13TH Auto-Heal Logs</h2>
    <div style='border:1px solid #333;padding:10px;height:70vh;overflow:auto;'>{data}</div>
    </body></html>
    """
PY

# Inject into main.py if not already
if grep -q "FastAPI()" main.py 2>/dev/null && ! grep -q "heal.dashboard" main.py; then
    echo "🔗 Linking heal dashboard route into main.py..."
    sed -i "1i from heal.dashboard import router as heal_router" main.py
    sed -i "/FastAPI()/a app.include_router(heal_router)" main.py
fi

##########################################
# 3️⃣ Watchdog + TUI + Discord alerts
##########################################
cat > watchdog.py << 'PY'
import time, subprocess, sys, requests, os

WEBHOOK = os.getenv("DISCORD_WEBHOOK")

def run_fix():
    print("🩺 Running fix_all.py...")
    subprocess.run([sys.executable, "fix_all.py"])

def start_server():
    return subprocess.Popen(["uvicorn", "main:app", "--reload"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

while True:
    print("🚀 Launching THE13TH server with watchdog...")
    p = start_server()
    for line in p.stdout:
        print(line, end="")
        if any(err in line for err in ["Traceback", "Error", "Exception"]):
            print("⚠️ Crash detected! Triggering repair...")
            if WEBHOOK:
                requests.post(WEBHOOK, json={"content": "🚨 **Server crashed, auto-repair triggered**"})
            p.kill()
            run_fix()
            break
    time.sleep(3)
PY

cat > fix_tui.py << 'PY'
import subprocess, os, time

def run(cmd):
    print(f"\n$ {cmd}")
    subprocess.run(cmd, shell=True)

while True:
    print("""
┌───────────────────────── THE13TH Repair Console ─────────────────────────┐
1) Run full fix_all.py
2) Restart server
3) Rebuild DB schema
4) Pin ENV hash
5) View logs
6) Git push repair commit
7) Tail live logs
0) Exit
└──────────────────────────────────────────────────────────────────────────┘
""")
    c = input("Option: ")
    if c == "1": run("python3 fix_all.py")
    elif c == "2": run("pkill -f uvicorn; uvicorn main:app --reload &")
    elif c == "3": run("python3 fix_all.py")
    elif c == "4": run("python3 fix_all.py")
    elif c == "5": run("tail -n 200 uvicorn_fix.log")
    elif c == "6": run("git add . && git commit -m 'auto repair' && git push")
    elif c == "7": run("tail -f uvicorn_fix.log")
    elif c == "0": print("👋 Goodbye"); break
PY

##########################################
# 4️⃣ GitHub + Docker heal integration
##########################################
mkdir -p .github/workflows
cat > .github/workflows/predeploy-fix.yml << 'YML'
name: Pre-Deploy Auto-Heal

on:
  push:
    branches: [ "main" ]

jobs:
  repair:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.12"
      - name: Auto-Heal before deploy
        run: |
          pip install -r requirements.txt || true
          python3 fix_all.py
      - name: Commit AutoFix
        run: |
          git config user.name "HealBot"
          git config user.email "healbot@the13th.ai"
          git add .
          git commit -m "auto-heal: pre-deploy repair" || true
          git push || true
YML

if [ ! -f Dockerfile ]; then
cat > Dockerfile << 'DOCKER'
FROM python:3.12
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt || true
HEALTHCHECK --interval=20s CMD curl -f http://localhost:8000/admin/login || exit 1
CMD ["python3", "-c", "import os; os.system('python3 fix_all.py'); os.execvp('uvicorn',['uvicorn','main:app','--host','0.0.0.0','--port','8000'])"]
DOCKER
else
grep -q "HEALTHCHECK" Dockerfile || echo "HEALTHCHECK CMD curl -f http://localhost:8000/admin/login || exit 1" >> Dockerfile
grep -q "fix_all.py" Dockerfile || echo 'CMD ["python3","-c","import os; os.system(\"python3 fix_all.py\"); os.execvp(\"uvicorn\",[\"uvicorn\",\"main:app\",\"--host\",\"0.0.0.0\",\"--port\",\"8000\"])]' >> Dockerfile
fi

##########################################
# ✅ Done
##########################################
echo "✅ Full self-healing system deployed successfully!"
echo ""
echo "➡ To view dashboard: http://localhost:8000/heal/logs"
echo "➡ To start self-healing server: python3 watchdog.py"
echo "➡ To repair manually: python3 fix_all.py"
echo "➡ To open dashboard console: python3 fix_tui.py"
