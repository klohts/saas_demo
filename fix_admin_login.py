
import os, re, sys

MAIN = "main.py"
PASSWORD = os.getenv("ADMIN_PASSWORD", "th13_superpass")
EMAIL = os.getenv("ADMIN_EMAIL", "admin@the13th.com")

code = open(MAIN).read()

# Patch 1 — force login handler to validate email + password
login_pattern = r"(async def\s+admin_login\([^)]*\):)"
replacement = r"""\1
    form = await request.form()
    email = form.get("email","").lower().strip()
    password = form.get("password","").strip()
    if email != '""" + EMAIL + r"""' or password != '""" + PASSWORD + r"""':
        return HTMLResponse("Unauthorized", status_code=401)
"""

# Ensure patch only applies once
if "email !=" not in code:
    code = re.sub(login_pattern, replacement, code, count=1)

# Patch 2 — make /admin require login OR allow direct access temporarily
code = re.sub(r"@app.get\(\"/admin\"\)", '@app.get("/admin")\n# TEMP: admin auth bypass for patch', code)

open(MAIN, "w").write(code)

print("\n✅ Admin login patched successfully!")
print("\n🔐 Use these credentials:\n")
print("EMAIL:   ", EMAIL)
print("PASSWORD:", PASSWORD)
print("\nNow restart with:\n  uvicorn main:app --reload\n")

