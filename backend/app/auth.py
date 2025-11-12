
import os
import base64
from fastapi import Request, HTTPException, status
from typing import Tuple


def _get_basic_credentials() -> Tuple[str, str]:
    user = os.getenv("BASIC_AUTH_USER")
    pwd = os.getenv("BASIC_AUTH_PASS")
    if not user or not pwd:
        return ("", "")
    return (user, pwd)


def require_basic_auth(request: Request):
    expected_user, expected_pass = _get_basic_credentials()
    auth = request.headers.get("Authorization")
    if not expected_user and not expected_pass:
        return True

    if not auth or not auth.startswith("Basic "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized",
                            headers={"WWW-Authenticate": "Basic"})
    try:
        payload = base64.b64decode(auth.split(" ", 1)[1]).decode()
        user, pwd = payload.split(":", 1)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized",
                            headers={"WWW-Authenticate": "Basic"})
    if not (user == expected_user and pwd == expected_pass):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized",
                            headers={"WWW-Authenticate": "Basic"})
    return True
