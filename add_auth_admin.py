#!/usr/bin/env python3
import os, sys

project_root = os.path.dirname(os.path.abspath(__file__))
auth_file = os.path.join(project_root, "utils", "auth_magic.py")

if not os.path.exists(auth_file):
    print("❌ auth_magic.py not found at utils/auth_magic.py")
    sys.exit(1)

with open(auth_file, "r") as f:
    content = f.read()

if "def auth_admin" in content:
    print("✅ auth_admin already exists. No changes made.")
    sys.exit(0)

patch = """

from fastapi import Request, HTTPException

async def auth_admin(request: Request):
    \"\"\"
    Simple admin guard using session cookie or Authorization header
    \"\"\"
    import sqlite3, os
    token = request.cookies.get("admin_session") or request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db = os.path.join(os.path.dirname(__file__), "..", "sessions.db")
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("SELECT role, expires_at FROM sessions WHERE token = ?", (token,))
    row = c.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid session")

    role, expires = row
    from datetime import datetime
    if role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    if datetime.fromisoformat(expires) < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Session expired")
    return True

"""

with open(auth_file, "a") as f:
    f.write(patch)

print("✅ auth_admin added successfully to utils/auth_magic.py")
