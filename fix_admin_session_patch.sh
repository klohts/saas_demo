#!/usr/bin/env bash
set -e

MAIN=main.py
BACKUP=main.py.bak.$(date +%s)
echo "Backing up $MAIN -> $BACKUP"
cp "$MAIN" "$BACKUP"

echo "Commenting out old admin cookie-based handlers + register/patch calls..."
# comment lines from the admin cookie section start to the end of that block
# we look for the marker "ADMIN_PASSWORD = os.getenv" (unique in your file) and comment until the two calls register_admin_routes/patch_operator_audit
awk '
BEGIN{p=1}
/^ADMIN_PASSWORD = os.getenv/ {p=0}
{ if(p) print $0; else print "#OLD#"$0 }
' "$BACKUP" > "$MAIN.tmp" && mv "$MAIN.tmp" "$MAIN"

# Now uncomment the file but preserve the commented blocks; the next step will comment the register/patch lines fully
sed -i 's/^#OLD#\(.*register_admin_routes(app, templates).*//g' "$MAIN" || true
# Make sure register_admin_routes and patch_operator_audit calls are commented
sed -i 's/^.*register_admin_routes(app, templates).*$/#COMMENTED: register_admin_routes removed/g' "$MAIN" || true
sed -i 's/^.*patch_operator_audit(app).*$/#COMMENTED: patch_operator_audit removed/g' "$MAIN" || true

echo "Appending a single session-based admin flow (email+password -> session_token)."
cat >> "$MAIN" <<'PYCODE'

# === Unified Session-based Admin Flow (replaces older cookie-based handlers) ===
from fastapi import Form, Depends
from fastapi.responses import RedirectResponse

# admin credentials functions expected from utils/auth_magic.py:
#   verify_admin_credentials(email, password)
#   create_admin_session()
#   auth_admin (dependency that validates session_token)
#
# Ensure those exist in utils/auth_magic (we previously added them).

@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    # render template; template should include fields name="email" and name="password"
    return templates.TemplateResponse("admin_login.html", {"request": request})

@app.post("/admin/login")
async def admin_login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    # verify credentials
    if verify_admin_credentials(email, password):
        token = create_admin_session()
        resp = RedirectResponse(url="/admin/tools", status_code=303)
        resp.set_cookie(key="session_token", value=token, httponly=True, max_age=6*3600)
        return resp
    # failed login -> re-render with error
    return templates.TemplateResponse("admin_login.html", {"request": request, "error": "Invalid credentials"}, status_code=401)

@app.get("/admin/logout")
def admin_logout(request: Request):
    resp = RedirectResponse(url="/admin/login", status_code=303)
    resp.delete_cookie("session_token")
    return resp

@app.get("/admin/tools", response_class=HTMLResponse)
def admin_tools(request: Request, session_token: str = Depends(auth_admin)):
    return templates.TemplateResponse("admin_tools.html", {"request": request})

@app.post("/admin/reset-logs")
def reset_logs(session_token: str = Depends(auth_admin)):
    from pathlib import Path
    for f in Path("logs").glob("*.log"):
        try:
            f.write_text("")
        except Exception:
            pass
    return RedirectResponse("/admin/tools", status_code=303)

@app.post("/admin/filter-emails")
def filter_failed_emails(session_token: str = Depends(auth_admin)):
    from pathlib import Path
    log_path = Path("logs/email_delivery.log")
    if log_path.exists():
        failed_lines = [line for line in log_path.read_text().splitlines() if "FAILED" in line]
        log_path.write_text("\n".join(failed_lines))
    return RedirectResponse("/admin/tools", status_code=303)

@app.post("/admin/toggle-demo")
def toggle_demo(session_token: str = Depends(auth_admin)):
    global DEMO_MODE
    DEMO_MODE = not DEMO_MODE
    status = "activated" if DEMO_MODE else "deactivated"
    return HTMLResponse(f"<h3>🟣 Demo mode {status}.</h3><a href='/admin/tools'>Back</a>")
# === End unified admin block ===

PYCODE

echo "Formatting check (quick grep for duplicates)..."
grep -n "/admin/login" "$MAIN" || true

echo "Patch applied. Backup at: $BACKUP"
echo "Now restart your server: uvicorn main:app --reload"
