#!/bin/bash
echo "🩹 Applying Stage 13.5.1 — Admin Auth + Cookie Fix..."

# Ensure ADMIN_PASSWORD is defined in .env
if ! grep -q "ADMIN_PASSWORD" .env; then
  echo "ADMIN_PASSWORD=th13_superpass" >> .env
  echo "✅ Added ADMIN_PASSWORD to .env (default: th13_superpass)"
fi

# Inject improved login + cookie logic
cat > utils/patch_adminauth_fix.py <<'PYCODE'
from fastapi import Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
import os
from pathlib import Path

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "th13_superpass")
DEMO_MODE = True

def register_admin_routes(app, templates):

    def require_admin_auth(request: Request):
        if request.cookies.get("auth") != "1":
            raise HTTPException(status_code=403, detail="Unauthorized")

    @app.get("/admin/login", response_class=HTMLResponse)
    def admin_login_page(request: Request):
        return templates.TemplateResponse("admin_login.html", {"request": request})

    @app.post("/admin/login", response_class=HTMLResponse)
    def admin_login_submit(request: Request, password: str = Form(...)):
        if password.strip() == ADMIN_PASSWORD:
            response = RedirectResponse(url="/admin/tools", status_code=303)
            response.set_cookie("auth", "1", httponly=True, max_age=3600)
            return response
        return HTMLResponse("<h3>❌ Invalid password</h3><a href='/admin/login'>Try again</a>", status_code=403)

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

# Ensure it's imported into main.py
if ! grep -q "register_admin_routes" main.py; then
  sed -i '/from fastapi.staticfiles/a from utils.patch_adminauth_fix import register_admin_routes' main.py
  echo "" >> main.py
  echo "register_admin_routes(app, templates)" >> main.py
  echo "✅ Linked admin auth patch in main.py"
fi

echo "💾 Committing patch..."
git add utils/patch_adminauth_fix.py main.py .env
git commit -m "Fix admin login + cookie redirect (Stage 13.5.1)"
git push origin main

echo "🚀 Redeploy or restart with: uvicorn main:app --reload"
echo "➡ Then visit: http://127.0.0.1:8000/admin/login"
