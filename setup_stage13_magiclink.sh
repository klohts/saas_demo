#!/bin/bash
echo "🪄 Setting up THE13TH Stage 13 (v4.9.0) — Magic Link Client Portal..."

# Ensure directories exist
mkdir -p utils templates static logs

# 1️⃣ Create utils/auth_magic.py
cat > utils/auth_magic.py <<'PYCODE'
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
PYCODE

# 2️⃣ Add templates
mkdir -p templates

cat > templates/client_signup.html <<'HTML'
<!doctype html>
<html>
<head><title>THE13TH Sign In</title>
<link rel="stylesheet" href="/static/the13th.css">
</head>
<body class="page">
<h2>🔮 Sign in to THE13TH</h2>
<form action="/api/magic-link" method="get">
  <input type="email" name="email" placeholder="Enter your email" required>
  <button type="submit">Send Magic Link</button>
</form>
</body>
</html>
HTML

cat > templates/client_dashboard.html <<'HTML'
<!doctype html>
<html>
<head><title>THE13TH Dashboard</title>
<link rel="stylesheet" href="/static/the13th.css">
</head>
<body class="page">
<div class="demo-banner">⚙️ Demo Mode Active</div>
<h2>Welcome, {{ email }} ✨</h2>
<p>Requests Today: {{ metrics.requests_today }}</p>
<p>Avg Duration: {{ metrics.avg_duration_ms }} ms</p>
<a href="/">← Back Home</a>
</body>
</html>
HTML

# 3️⃣ Patch main.py with new routes if not already added
if ! grep -q "create_magic_link" main.py; then
  echo "🔧 Patching main.py for Magic Link routes..."
  cat >> main.py <<'PYCODE'

# === Stage 13: Magic Link Client Portal ===
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from utils.auth_magic import init_db, create_magic_link, validate_token
from utils.telemetry import parse_today_metrics

templates = Jinja2Templates(directory="templates")
init_db()

@app.get("/client/signup", response_class=HTMLResponse)
def client_signup():
    return templates.TemplateResponse("client_signup.html", {"request": {}})

@app.get("/api/magic-link")
def magic_link(email: str):
    link = create_magic_link(email)
    return {"email": email, "magic_link": link}

@app.get("/client/login", response_class=HTMLResponse)
def client_login(token: str):
    email = validate_token(token)
    if not email:
        return HTMLResponse("<h2>Invalid or expired link.</h2>", status_code=401)
    response = RedirectResponse(url="/client/dashboard")
    response.set_cookie(key="session_user", value=email, max_age=3600)
    return response

@app.get("/client/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    email = request.cookies.get("session_user")
    if not email:
        return RedirectResponse(url="/client/signup")
    metrics = parse_today_metrics()
    return templates.TemplateResponse("client_dashboard.html",
        {"request": request, "email": email, "metrics": metrics})
PYCODE
else
  echo "✅ Magic Link routes already exist in main.py"
fi

echo "💾 Committing Stage 13 files..."
git add utils/auth_magic.py templates/client_*.html main.py
git commit -m "Add Stage 13 Magic Link Client Portal (v4.9.0)"
git push origin main

echo "🚀 Stage 13 setup complete."
echo "➡ Run with: uvicorn main:app --reload"
echo "Then visit: http://127.0.0.1:8000/client/signup"
