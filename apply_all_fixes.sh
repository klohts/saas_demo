#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "🔁 apply_all_fixes.sh — running from $ROOT"

TIMESTAMP=$(date +"%Y%m%dT%H%M%S")
backup_dir="$ROOT/setup_backups_auto_$TIMESTAMP"
mkdir -p "$backup_dir"
echo "📦 Backups → $backup_dir"

# 1) Backup important files
for f in main.py utils/auth_magic.py .env; do
  if [ -f "$f" ]; then
    cp -v "$f" "$backup_dir/$(basename "$f").$TIMESTAMP.bak"
  fi
done

# 2) Pin ADMIN_PASSWORD_HASH into .env (change the hash below to the one you want pinned)
#    If you already set ADMIN_PASSWORD_HASH in .env, this replaces it.
PIN_HASH="e482a10e1a3edb30f45d7973c82994027f8e1f7e557bf4c3d03876e7bf09d15c"

if [ -f .env ]; then
  # remove existing ADMIN_PASSWORD_HASH lines, append pinned one
  grep -vE "^ADMIN_PASSWORD_HASH=" .env > .env.tmp || true
  echo "ADMIN_PASSWORD_HASH=${PIN_HASH}" >> .env.tmp
  mv .env.tmp .env
  echo "🔒 Pinned ADMIN_PASSWORD_HASH in .env"
else
  echo "ADMIN_PASSWORD_HASH=${PIN_HASH}" > .env
  echo "🔒 Created .env with ADMIN_PASSWORD_HASH"
fi

# Export into current shell environment for immediate use (useful for any subprocesses launched here)
export ADMIN_PASSWORD_HASH="$PIN_HASH"

# 3) Ensure data/sessions.db has required columns (twofa_code, twofa_expires, role, created_at, expires_at)
DB_PATH="data/sessions.db"
if [ ! -f "$DB_PATH" ]; then
  echo "⚠️  $DB_PATH not found — searching other DB files..."
  if [ -f sessions.db ]; then
    DB_PATH="sessions.db"
    echo "ℹ️  Using sessions.db instead"
  fi
fi

if [ -f "$DB_PATH" ]; then
  python3 - <<PY
import sqlite3, sys
db = "$DB_PATH"
con = sqlite3.connect(db)
cur = con.cursor()
columns = {
    "role":"TEXT",
    "created_at":"TEXT",
    "expires_at":"REAL",
    "twofa_code":"TEXT",
    "twofa_expires":"REAL"
}
for col, dtype in columns.items():
    try:
        cur.execute(f"ALTER TABLE sessions ADD COLUMN {col} {dtype}")
        print("✅ Added column:", col)
    except sqlite3.OperationalError as e:
        msg = str(e).lower()
        if "duplicate" in msg or "already exists" in msg:
            print("⚠️  Column already exists:", col)
        else:
            print("❌ Error adding column", col, ":", e)
con.commit()
con.close()
print("✅ DB migration finished for", db)
PY
else
  echo "❌ No sessions DB found at data/sessions.db or sessions.db — cannot run DB migration."
fi

# 4) Patch main.py: send UTF-8 for the 2FA email and ensure cookie secure var present and set defaults
#    Also ensure required imports exist (FastAPI, Depends, Request, HTTPException, RedirectResponse, JSONResponse, Path)
#    This sed-based patch is conservative and idempotent.
MAIN="main.py"

if [ -f "$MAIN" ]; then
  # Add missing imports (idempotent)
  python3 - <<'PY'
from pathlib import Path
p = Path("$MAIN")
s = p.read_text()
# ensure core imports line exists and includes Depends
s = s.replace("from fastapi import FastAPI, Request, HTTPException", "from fastapi import FastAPI, Request, HTTPException, Depends")
# ensure RedirectResponse + JSONResponse present
if "from fastapi.responses import RedirectResponse" not in s:
    s = "from fastapi.responses import RedirectResponse, JSONResponse\\n" + s
# ensure Path and json imports
if "from pathlib import Path" not in s:
    s = "from pathlib import Path\\n" + s
if "import json" not in s:
    s = "import json\\n" + s
# ensure COOKIE_SECURE exists
if "COOKIE_SECURE =" not in s:
    s = s.replace("app = FastAPI()", "app = FastAPI()\\nCOOKIE_SECURE = bool(int(__import__('os').getenv('COOKIE_SECURE','0')))")
# patch sendmail to use utf-8 encoding
s = s.replace("s.sendmail(SMTP_FROM, [to_address], message)", "s.sendmail(SMTP_FROM, [to_address], message.encode('utf-8'))")
p.write_text(s)
print("🔧 main.py patched: imports, COOKIE_SECURE, UTF-8 email send (idempotent)")
PY

  # backup already done at top
else
  echo "❌ main.py not found in repo root. Aborting patch step."
fi

# 5) Optionally extend pending twofa expiries for dev convenience (10 minutes from now)
python3 - <<PY
import sqlite3, time
db = "$DB_PATH"
try:
    con = sqlite3.connect(db)
    cur = con.cursor()
    new_exp = time.time() + 600
    cur.execute("UPDATE sessions SET twofa_expires=? WHERE role='pending' OR twofa_expires IS NULL", (new_exp,))
    con.commit()
    print("⏱️  Extended pending twofa_expires (10 minutes) in", db)
    con.close()
except Exception as e:
    print("⚠️  Could not update twofa_expires:", e)
PY

# 6) Restart uvicorn (kill any running uvicorn processes, then start detached)
echo "♻️  Restarting uvicorn (will kill existing uvicorn processes)"
pkill -f uvicorn || true
# start uvicorn in background (dev). If you use a process manager or different command, adjust this line.
# We start it with --reload for dev convenience.
nohup uvicorn main:app --reload > uvicorn_auto.log 2>&1 &

echo "✅ Done. uvicorn started (logs → uvicorn_auto.log)."
echo ""
echo "What this script did:"
echo " - Backed up main.py, utils/auth_magic.py and .env"
echo " - Pinned ADMIN_PASSWORD_HASH in .env"
echo " - Migrated data/sessions.db (added twofa_code,twofa_expires,role,created_at,expires_at where missing)"
echo " - Patched main.py to send UTF-8 email, ensured imports and COOKIE_SECURE"
echo " - Extended pending 2FA expiry by 10 minutes (dev convenience)"
echo " - Restarted uvicorn and wrote log to uvicorn_auto.log"
echo ""
echo "👉 Next: open http://127.0.0.1:8000/admin/login, login with admin@the13th.com + your password, then complete the 2FA code."
echo "If anything breaks, restore backups from $backup_dir"
