#!/usr/bin/env python3
import os, re

ROOT = os.getcwd()
TEMPLATES = os.path.join(ROOT, "templates")
UTILS = os.path.join(ROOT, "utils")
AUTH = os.path.join(UTILS, "auth_magic.py")
MAIN = os.path.join(ROOT, "main.py")

os.makedirs(TEMPLATES, exist_ok=True)
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)

# ---- 1. Admin Login Template ----
with open(os.path.join(TEMPLATES, "admin_login.html"), "w") as f:
    f.write("""<!doctype html>
<html><head><meta charset="utf-8"/><title>Login — THE13TH</title></head>
<body>
<h2>Admin Login</h2>
<form method="post" action="/admin/login">
  <input name="email" placeholder="Email" required /><br/>
  <input type="password" name="password" placeholder="Password" required /><br/>
  <button type="submit">Login</button>
</form>
</body></html>""")

# ---- 2. Admin Dashboard Template ----
with open(os.path.join(TEMPLATES, "admin_tools.html"), "w") as f:
    f.write("""<!doctype html>
<html><body>
<h2>THE13TH Admin Panel</h2>
<a href="/admin/logout">Logout</a>
<p>If you see this, login + middleware + session are working ✅</p>
</body></html>""")

print("✅ Templates created")

# ---- 3. Append auth_admin if missing ----
auth_patch = """

from fastapi import Request, HTTPException
def auth_admin(request: Request):
    import os, sqlite3, time
    token = request.cookies.get("session_token") or request.headers.get("Authorization")
    if not token:
        raise HTTPException(401, "Unauthorized")
    db = os.path.join(os.path.dirname(__file__), "..", "data", "sessions.db")
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("SELECT role, expires_at FROM sessions WHERE token=?", (token,))
    row = c.fetchone(); conn.close()
    if not row:
        raise HTTPException(401, "Invalid session")
    role, exp = row
    if exp and float(exp) < time.time():
        raise HTTPException(401, "Session expired")
    if role != "admin":
        raise HTTPException(403, "Forbidden")
    return token
"""
with open(AUTH, "r") as f: txt = f.read()
if "def auth_admin" not in txt:
    with open(AUTH, "a") as f: f.write(auth_patch)
    print("✅ auth_admin added")
else:
    print("⚠️ auth_admin already exists, skipped")

# ---- 4. Patch main.py ----
with open(MAIN, "r") as f: main = f.read()

# Ensure init_db import exists
if "from utils.auth_magic import init_db" not in main:
    main = "from utils.auth_magic import init_db\n" + main

# Insert middleware if not there
if "AdminLoaderMiddleware" not in main:
    middleware = """

from starlette.middleware.base import BaseHTTPMiddleware
class AdminLoaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        token = request.cookies.get("session_token")
        request.state.admin_user = None
        if token:
            try:
                import sqlite3, os, time
                db = os.path.join(os.getcwd(), "data", "sessions.db")
                conn = sqlite3.connect(db)
                c = conn.cursor()
                c.execute("SELECT email, role, expires_at FROM sessions WHERE token=?", (token,))
                row = c.fetchone(); conn.close()
                if row:
                    email, role, exp = row
                    if not exp or float(exp) > time.time():
                        request.state.admin_user = {"email": email, "role": role}
            except:
                pass
        return await call_next(request)

app.add_middleware(AdminLoaderMiddleware)
"""
    main = main.replace("app = FastAPI()", "app = FastAPI()" + middleware)

# Ensure /admin/tools exists
if "@app.get(\"/admin/tools\"" not in main:
    tools_route = """

from fastapi.responses import HTMLResponse
from datetime import datetime

@app.get("/admin/tools", response_class=HTMLResponse, dependencies=[Depends(auth_admin)])
def admin_tools(request: Request):
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="templates")
    return templates.TemplateResponse("admin_tools.html", {"request": request, "datetime": datetime})
"""
    main += tools_route

# Ensure /admin/login exists
if "@app.post(\"/admin/login\"" not in main:
    login_route = """

from fastapi.responses import RedirectResponse
from utils.auth_magic import verify_admin_credentials, create_admin_session

@app.post("/admin/login")
def admin_login(email: str = Form(...), password: str = Form(...)):
    if not verify_admin_credentials(password):
        return RedirectResponse("/admin/login?error=1", 302)
    token = create_admin_session()
    res = RedirectResponse("/admin/tools", 302)
    res.set_cookie("session_token", token, httponly=True, samesite="lax")
    return res
"""
    main += login_route

# Ensure /admin/logout exists
if "@app.get(\"/admin/logout\"" not in main:
    logout_route = """

@app.get("/admin/logout")
def admin_logout():
    res = RedirectResponse("/admin/login", 302)
    res.delete_cookie("session_token")
    return res
"""
    main += logout_route

with open(MAIN, "w") as f: f.write(main)
print("✅ main.py patched")

# ---- 5. Dockerfile ----
with open(os.path.join(ROOT, "Dockerfile"), "w") as f:
    f.write("""FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache -r requirements.txt || pip install fastapi uvicorn requests
RUN mkdir -p /app/data /app/logs
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
""")

print("✅ Dockerfile written")
print("\\n🚀 Done. Now run:\\n  uvicorn main:app --reload\\n")
