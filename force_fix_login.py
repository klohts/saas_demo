import re

f = "main.py"
code = open(f).read()

# 1. Remove any existing login endpoints completely
code = re.sub(r"@app\.post\(.*/admin/login.*?[^\n]*\n(    .*\n)+", "\n", code)

# 2. Ensure required imports exist
imports = [
    "from fastapi import FastAPI, Request, HTTPException, Depends, Form, Response",
    "from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse",
    "from pathlib import Path",
    "import json"
]

for imp in imports:
    if imp not in code:
        code = imp + "\n" + code

# 3. Inject correct login endpoint BEFORE first protected route or first decorator
login_endpoint = """

@app.post("/admin/login")
def admin_login(password: str = Form(...), response: Response = None):
    if password != "admin123":
        return HTMLResponse("<h3>❌ Invalid password</h3>", status_code=401)

    res = RedirectResponse("/admin/tools", status_code=303)
    res.set_cookie(key="session_token", value="admin_session_token", httponly=True)
    return res

"""

# Insert before first @app. occurrence
code = re.sub(r"(@app\.)", login_endpoint + r"\n\1", code, count=1)

# 4. Rewrite file
open(f, "w").write(code)
print("✅ Login route force-injected and query password removed.")
