import re

target = "main.py"
code = open(target).read()

# 1. Remove the broken ".join(failed))" line completely
code = re.sub(r'^.*join\\(failed\\)\\).*$\\n?', '', code, flags=re.MULTILINE)

# 2. Remove lines that start with stray backslashes
code = re.sub(r'^\\\\+.*$', '', code, flags=re.MULTILINE)

# 3. Ensure essential imports exist
if "from fastapi import Request" not in code:
    code = code.replace(
        "from fastapi import FastAPI",
        "from fastapi import FastAPI, Request, HTTPException",
        1
    )

# 4. Guarantee auth_admin function exists correctly
auth_func = """
async def auth_admin(request: Request):
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if token != "admin_session_token":
        raise HTTPException(status_code=403, detail="Invalid session")
    return True
"""

if "async def auth_admin" in code:
    code = re.sub(
        r"async def auth_admin[\\s\\S]*?return.*?True",
        auth_func,
        code
    )
else:
    code += "\\n" + auth_func

# 5. Write cleaned file
open(target, "w").write(code)
print("✅ main.py cleaned and repaired!")
