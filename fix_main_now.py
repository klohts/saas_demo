import re

f = "main.py"
code = open(f).read()

# 1. Remove the catastrophic broken .join line
code = re.sub(r'^.*join\\(failed\\).*$', '', code, flags=re.MULTILINE)

# 2. Remove duplicate Request imports
code = re.sub(r'from fastapi import Request\\n', '', code)
code = re.sub(r'from fastapi import Request, HTTPException', 'from fastapi import Request, HTTPException', code, 1)

# 3. Ensure auth_admin is a clean valid function
auth_clean = """
async def auth_admin(request: Request):
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if token != "admin_session_token":
        raise HTTPException(status_code=403, detail="Invalid session")
    return True
"""

code = re.sub(
    r'async def auth_admin[\\s\\S]*?return True',
    auth_clean.strip(),
    code
)

# 4. Save repaired file
open(f, "w").write(code.strip() + "\\n")
print("✅ main.py fixed!")
