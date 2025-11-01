from fastapi import Request, HTTPException, status
from dotenv import load_dotenv
import os

load_dotenv()

def _active_key() -> str | None:
    return os.getenv("X_API_KEY") or os.getenv("APP_API_KEY")

async def verify_api_key(request: Request):
    key = _active_key()
    if not key:
        raise HTTPException(status_code=500, detail="Server missing API key configuration")

    header_key = request.headers.get("X-API-Key")
    query_key = request.query_params.get("api_key")

    if header_key == key or query_key == key:
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing X-API-Key")
