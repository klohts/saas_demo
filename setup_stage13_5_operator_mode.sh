#!/bin/bash
echo "🔐 Setting up THE13TH Stage 13.5 — Operator Mode (Admin Auth + Tools)..."

mkdir -p templates

# 1️⃣ Admin Login HTML
cat > templates/admin_login.html <<'HTML'
<!doctype html>
<html>
<head>
  <title>THE13TH — Admin Login</title>
  <link rel="stylesheet" href="/static/the13th.css">
  <style>
    body { display: flex; align-items: center; justify-content: center; height: 100vh; }
    form { background: #111; padding: 2em; border-radius: 12px; box-shadow: 0 0 15px #a855f7; }
    input { display: block; margin: 1em 0; width: 100%; padding: 0.8em; background: #222; border: 1px solid #444; color: #eee; border-radius: 8px; }
    button { padding: 0.7em 1.2em; background: #a855f7; color: white; border: none; border-radius: 8px; cursor: pointer; }
  </style>
</head>
<body>
<form method="POST" action="/admin/login">
  <h2>🔐 Admin Login</h2>
  <input name="password" type="password" placeholder="Enter admin password" required>
  <button type="submit">Login</button>
</form>
</body>
</html>
HTML

# 2️⃣ Operator Tools HTML
cat > templates/admin_tools.html <<'HTML'
<!doctype html>
<html>
<head>
  <title>THE13TH — Operator Tools</title>
  <link rel="stylesheet" href="/static/the13th.css">
  <style>
    .tools { display: flex; flex-direction: column; gap: 1em; max-width: 400px; margin: 3em auto; }
    button { padding: 0.8em; border: none; border-radius: 10px; cursor: pointer; font-size: 1em; }
    .reset { background: #f87171; color: #fff; }
    .filter { background: #3b82f6; color: #fff; }
    .toggle { background: #10b981; color: #fff; }
    a { color: #a855f7; text-decoration: none; }
  </style>
</head>
<body class="page">
  <h1>🧠 THE13TH Operator Panel</h1>
  <div class="tools">
    <form action="/admin/reset-logs" method="post"><button class="reset">🧹 Reset Logs</button></form>
    <form action="/admin/filter-emails" method="post"><button class="filter">📧 Filter Failed Emails</button></form>
    <form action="/admin/toggle-demo" method="post"><button class="toggle">⚙️ Toggle Demo Mode</button></form>
  </div>
  <footer><a href="/admin/overview">← Back to Dashboard</a></footer>
</body>
</html>
HTML

# 3️⃣ Add routes to main.py
if ! grep -q "/admin/login" main.py; then
cat >> main.py <<'PYCODE'

from fastapi import Form
from fastapi.responses import RedirectResponse

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "th13_superpass")
DEMO_MODE = True

@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})

@app.post("/admin/login", response_class=RedirectResponse)
def admin_login_submit(request: Request, password: str = Form(...)):
    if password.strip() == ADMIN_PASSWORD:
        response = RedirectResponse(url="/admin/tools", status_code=302)
        response.set_cookie("auth", "1", httponly=True)
        return response
    return HTMLResponse("<h3>❌ Invalid password</h3><a href='/admin/login'>Try again</a>", status_code=403)

def require_admin_auth(request: Request):
    if request.cookies.get("auth") != "1":
        raise HTTPException(status_code=403, detail="Unauthorized")

@app.get("/admin/tools", response_class=HTMLResponse)
def admin_tools(request: Request):
    require_admin_auth(request)
    return templates.TemplateResponse("admin_tools.html", {"request": request})

@app.post("/admin/reset-logs")
def reset_logs(request: Request):
    require_admin_auth(request)
    for f in Path("logs").glob("*.log"):
        f.write_text("")
    return RedirectResponse("/admin/tools", status_code=302)

@app.post("/admin/filter-emails")
def filter_failed_emails(request: Request):
    require_admin_auth(request)
    log_path = Path("logs/email_delivery.log")
    if log_path.exists():
        failed_lines = [line for line in log_path.read_text().splitlines() if "FAILED" in line]
        log_path.write_text("\n".join(failed_lines))
    return RedirectResponse("/admin/tools", status_code=302)

@app.post("/admin/toggle-demo")
def toggle_demo(request: Request):
    require_admin_auth(request)
    global DEMO_MODE
    DEMO_MODE = not DEMO_MODE
    status = "activated" if DEMO_MODE else "deactivated"
    return HTMLResponse(f"<h3>🟣 Demo mode {status}.</h3><a href='/admin/tools'>Back</a>")
PYCODE
  echo "✅ Added admin auth and operator routes."
else
  echo "⚙️ Admin auth already exists."
fi

# 4️⃣ Commit and push
git add templates/admin_login.html templates/admin_tools.html main.py
git commit -m "Add Stage 13.5 Operator Mode (Admin Auth + Tools)"
git push origin main

echo "🚀 Stage 13.5 setup complete!"
echo "➡ Restart with: uvicorn main:app --reload"
echo "➡ Visit: http://127.0.0.1:8000/admin/login"
