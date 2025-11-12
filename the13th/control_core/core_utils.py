from __future__ import annotations
import os
from fastapi import Header, HTTPException, status
import httpx
from contextlib import asynccontextmanager

SYS_API_KEY = os.getenv('CC_SYS_API_KEY', 'supersecret_sys_key')

def require_sys_api_key(x_sys_api_key: str | None = Header(None)):
    if x_sys_api_key is None or x_sys_api_key != SYS_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid system API key')

@asynccontextmanager
async def get_http_client(timeout: int = 10):
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=25)
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        yield client
