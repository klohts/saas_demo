#!/bin/bash
echo "📡 Setting up THE13TH Stage 13.3 — Email Monitor & Webhook Alerts..."

# Ensure directories exist
mkdir -p utils templates logs

# 1️⃣ Add email log viewer template
cat > templates/email_log.html <<'HTML'
<!doctype html>
<html>
<head>
  <title>THE13TH — Email Delivery Log</title>
  <link rel="stylesheet" href="/static/the13th.css">
</head>
<body class="page">
<h2>📧 Email Delivery Log</h2>
<div class="card">
  <pre style="font-size:14px; background:#111; color:#0f0; padding:1em; border-radius:8px;">
{{ log_content }}
  </pre>
</div>
<footer><a href="/">← Back to Home</a></footer>
</body>
</html>
HTML

# 2️⃣ Patch utils/auth_magic.py to add webhook notification helper
UTILS_PATH="utils/auth_magic.py"
if ! grep -q "def notify_webhook" $UTILS_PATH; then
cat >> $UTILS_PATH <<'PYCODE'

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
PYCODE
  echo "🧩 Added webhook and enhanced log_email_delivery in $UTILS_PATH"
else
  echo "✅ Webhook already integrated."
fi

# 3️⃣ Patch main.py with /admin/email-log route
if ! grep -q "/admin/email-log" main.py; then
cat >> main.py <<'PYCODE'

# === Stage 13.3: Email Log Viewer ===
@app.get("/admin/email-log", response_class=HTMLResponse)
def view_email_log(request: Request):
    from pathlib import Path
    log_path = Path("logs/email_delivery.log")
    if not log_path.exists():
        content = "No log entries yet."
    else:
        content = log_path.read_text()[-5000:]  # last 5k chars
    return templates.TemplateResponse("email_log.html",
        {"request": request, "log_content": content})
PYCODE
  echo "🧩 Added /admin/email-log route to main.py"
else
  echo "✅ /admin/email-log route already present."
fi

# 4️⃣ Update .env with webhook placeholder
if ! grep -q "WEBHOOK_URL" .env; then
cat >> .env <<'ENV'
# Optional Slack or Discord Webhook for Email Alerts
WEBHOOK_URL=
ENV
  echo "⚙️  Added WEBHOOK_URL placeholder to .env"
else
  echo "✅ WEBHOOK_URL already defined in .env"
fi

echo "💾 Committing Stage 13.3 changes..."
git add utils/auth_magic.py templates/email_log.html main.py .env
git commit -m "Add Stage 13.3 Email Monitor & Webhook Alerts"
git push origin main

echo "🚀 Stage 13.3 setup complete!"
echo "➡ Restart with: uvicorn main:app --reload"
echo "➡ Visit: http://127.0.0.1:8000/admin/email-log"
