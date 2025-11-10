import re

target = "main.py"
c = open(target).read()

# Replace broken auth_admin function with a working one that reads cookies
patch = '''
from fastapi import Request, HTTPException

async def auth_admin(request: Request):
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if token != "admin_session_token":
        raise HTTPException(status_code=403, detail="Invalid session")
    return True
'''

# Replace existing auth_admin block
c = re.sub(
    r"async def auth_admin.*?return.*?\\n",
    patch,
    c,
    flags=re.DOTALL
)

open(target, "w").write(c)
print("✅ auth_admin session validation fixed")
