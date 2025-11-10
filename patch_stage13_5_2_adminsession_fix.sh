#!/bin/bash
echo "🩹 Applying Stage 13.5.2 — Definitive Admin Auth & Session Fix..."

# 1️⃣ Ensure python-dotenv is installed and .env includes password + secret key
pip install python-dotenv > /dev/null 2>&1

if ! grep -q "ADMIN_PASSWORD" .env; then
  echo "ADMIN_PASSWORD=th13_superpass" >> .env
  echo "✅ Added ADMIN_PASSWORD=th13_superpass to .env"
fi

if ! grep -q "SESSION_SECRET_KEY" .env; then
  echo "SESSION_SECRET_KEY=th13_secretkey_123" >> .env
  echo "✅ Added SESSION_SECRET_KEY to .env"
fi

# 2️⃣ Inject session middleware into main.py
if ! grep -q "SessionMiddleware" main.py; then
  sed -i '/from fastapi.middleware.cors/a from starlette.middleware.sessions import SessionMiddleware' main.py
  sed -i "/app = FastAPI()/a app.add_middleware(SessionMiddleware, secret_key=os.getenv('SESSION_SECRET_KEY', 'th13_secretkey_123'))"
  echo "✅ Added SessionMiddleware to main.py"
fi

# 3️⃣ Replace admin auth block with a stable version that uses sessions
cat > utils/admin_auth_session_fix.py <<'PYCODE'
import os
from fastapi import Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "th13_superpass")
DEMO_MODE = True

def register_admin_routes(app, templates):

    def require_admin_auth(request: Request):
        if not request.session.get("is_admin"):
            raise HTTPException(status_code=403, detail="Unauthorized")

    @app.get("/admin/login", response_class=HTMLResponse)
    def admin_login_page(request: Request):
        return templates.TemplateResponse("admin_login.html", {"request": request})

    @app.post("/admin/login", response_class=RedirectResponse)
    async def admin_login_submit(request: Request, password: str = Form(...)):
        if password.strip() == ADMIN_PASSWORD:
            request.session["is_admin"] = True
            return RedirectResponse(url="/admin/tools", status_code=303)
        return HTMLResponse("<h3>❌ Invalid password</h3><a href='/admin/login'>Try again</a>", status_code=403)

    @app.get("/admin/logout", response_class=RedirectResponse)
    def admin_logout(request: Request):
        request.session.clear()
        return RedirectResponse(url="/admin/login", status_code=303)

    @app.get("/admin/tools", response_class=HTMLResponse)
    def admin_tools(request: Request):
        require_admin_auth(request)
        return templates.TemplateResponse("admin_tools.html", {"request": request})

    @app.post("/admin/reset-logs")
    def reset_logs(request: Request):
        require_admin_auth(request)
        for f in Path("logs").glob("*.log"):
            f.write_text("")
        return RedirectResponse("/admin/tools", status_code=303)

    @app.post("/admin/filter-emails")
    def filter_failed_emails(request: Request):
        require_admin_auth(request)
        log_path = Path("logs/email_delivery.log")
        if log_path.exists():
            failed_lines = [line for line in log_path.read_text().splitlines() if "FAILED" in line]
            log_path.write_text("\n".join(failed_lines))
        return RedirectResponse("/admin/tools", status_code=303)

    @app.post("/admin/toggle-demo")
    def toggle_demo(request: Request):
        require_admin_auth(request)
        global DEMO_MODE
        DEMO_MODE = not DEMO_MODE
        status = "activated" if DEMO_MODE else "deactivated"
        return HTMLResponse(f"<h3>🟣 Demo mode {status}.</h3><a href='/admin/tools'>Back</a>")
PYCODE

# 4️⃣ Wire this into main.py if not already linked
if ! grep -q "register_admin_routes(app, templates)" main.py; then
  sed -i '/from fastapi.staticfiles/a from utils.admin_auth_session_fix import register_admin_routes' main.py
  echo "" >> main.py
  echo "register_admin_routes(app, templates)" >> main.py
  echo "✅ Registered admin session fix routes in main.py"
else
  echo "⚙️ Admin routes already registered."
fi

# 5️⃣ Commit and redeploy
git add utils/admin_auth_session_fix.py main.py .env
git commit -m "Fix admin auth with session-based login (Stage 13.5.2)"
git push origin main

echo "🚀 Stage 13.5.2 applied successfully!"
echo "➡ Restart with: uvicorn main:app --reload"
echo "➡ Visit: http://127.0.0.1:8000/admin/login (password: th13_superpass)"
