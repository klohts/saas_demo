import re, sys, os, sqlite3

main = "main.py"
auth = "utils/auth_magic.py"

# --- 1. Ensure main.py reads session cookie correctly in auth dependency
patch1 = r"def auth_admin"
inject1 = """
async def auth_admin(request: Request):
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(401, "Not authenticated")

    from utils.auth_magic import get_session
    session = get_session(token)
    if not session or session.get("role") != "admin":
        raise HTTPException(401, "Not authenticated")

    request.state.admin = session
    return session
"""

# Replace or insert auth_admin
txt = open(main).read()
if "def auth_admin" in txt:
    txt = re.sub(r"def auth_admin[\\s\\S]*?return .*?\\n", inject1, txt)
else:
    txt = inject1 + "\\n" + txt
open(main, "w").write(txt)

# --- 2. Ensure we have a session reader in auth_magic.py
if "def get_session" not in open(auth).read():
    with open(auth, "a") as f:
        f.write("""
def get_session(token: str):
    import os, sqlite3
    db = os.path.join(os.path.dirname(__file__), "..", "sessions.db")
    con = sqlite3.connect(db)
    row = con.execute("SELECT token, email, role, created_at, expires_at FROM sessions WHERE token=?",(token,)).fetchone()
    con.close()
    if not row:
        return None
    return {"token": row[0], "email": row[1], "role": row[2], "created_at": row[3], "expires_at": row[4]}
""")

print("✅ Auth session fix applied.")
