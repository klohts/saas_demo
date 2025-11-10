#!/bin/bash
echo "🧩 Setting up THE13TH Stage 13.6 — Audit Events + Notifications..."

pip install requests > /dev/null 2>&1

# Ensure env vars
if ! grep -q "SLACK_WEBHOOK_URL" .env; then
  echo "SLACK_WEBHOOK_URL=" >> .env
fi
if ! grep -q "DISCORD_WEBHOOK_URL" .env; then
  echo "DISCORD_WEBHOOK_URL=" >> .env
fi
if ! grep -q "AUDIT_NOTIFICATIONS" .env; then
  echo "AUDIT_NOTIFICATIONS=true" >> .env
fi

# 🔧 Create utility
mkdir -p utils
cat > utils/admin_audit.py <<'PYCODE'
import os, json, requests
from datetime import datetime
from pathlib import Path

LOG_PATH = Path("logs/admin_audit.log")
SLACK = os.getenv("SLACK_WEBHOOK_URL")
DISCORD = os.getenv("DISCORD_WEBHOOK_URL")
NOTIFY = os.getenv("AUDIT_NOTIFICATIONS", "true").lower() == "true"

def record_audit(event:str, actor:str="admin"):
    LOG_PATH.parent.mkdir(exist_ok=True)
    entry = {
        "ts": datetime.utcnow().isoformat(),
        "actor": actor,
        "event": event,
    }
    LOG_PATH.write_text(LOG_PATH.read_text() + json.dumps(entry) + "\n" if LOG_PATH.exists() else json.dumps(entry) + "\n")

    if NOTIFY:
        payload = {"text": f"🧠 THE13TH Audit Event: {actor} → {event}"}
        try:
            if SLACK:
                requests.post(SLACK, json=payload, timeout=4)
            if DISCORD:
                requests.post(DISCORD, json={"content": payload["text"]}, timeout=4)
        except Exception:
            pass
PYCODE

# 🔧 Patch operator routes to emit audits
cat > utils/patch_operator_audit_inject.py <<'PYCODE'
from utils.admin_audit import record_audit

def patch_operator_audit(app):
    @app.post("/admin/reset-logs")
    async def reset_logs_audited(request):
        record_audit("Reset Logs executed")
        return await app.router.routes_by_name["reset_logs"].endpoint(request)

    @app.post("/admin/filter-emails")
    async def filter_emails_audited(request):
        record_audit("Filter Failed Emails executed")
        return await app.router.routes_by_name["filter_failed_emails"].endpoint(request)

    @app.post("/admin/toggle-demo")
    async def toggle_demo_audited(request):
        record_audit("Toggle Demo Mode executed")
        return await app.router.routes_by_name["toggle_demo"].endpoint(request)
PYCODE

# 🔧 Wire into main.py if missing
if ! grep -q "patch_operator_audit" main.py; then
  sed -i '/from fastapi.staticfiles/a from utils.patch_operator_audit_inject import patch_operator_audit' main.py
  echo "patch_operator_audit(app)" >> main.py
  echo "✅ Audit injector linked in main.py"
fi

git add utils/admin_audit.py utils/patch_operator_audit_inject.py main.py .env
git commit -m "Add Stage 13.6 Audit Events + Notifications"
git push origin main

echo "🚀 Stage 13.6 ready! Restart with: uvicorn main:app --reload"
echo "➡ Actions will now log to logs/admin_audit.log and notify Slack/Discord (if set)."
