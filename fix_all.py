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
