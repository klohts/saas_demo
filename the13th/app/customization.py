"""FastAPI router: client customization endpoints
Place this file at: the13th/app/customization.py
Import and include the router in your main FastAPI app as:

    from app.customization import router as customization_router
    app.include_router(customization_router, prefix="/api/customization")

This file reads client_customization.json and client_theme.json and exposes secure update endpoints (basic auth).
"""
from typing import Dict, Any
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

router = APIRouter()
BASE = Path(__file__).resolve().parents[1]
CUSTOM_FILE = BASE / "client_customization.json"
THEME_FILE = BASE / "client_theme.json"
security = HTTPBasic()

# Basic admin guard — reads credentials from environment to avoid hardcoding.
import os
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "changeme")


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


@router.get("/", summary="List all client customizations")
async def list_customizations():
    return _load_json(CUSTOM_FILE)


@router.get("/{client}", summary="Get customization for a client")
async def get_customization(client: str):
    data = _load_json(CUSTOM_FILE)
    if client not in data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="client not found")
    return data[client]


@router.get("/theme/default", summary="Get default theme")
async def get_default_theme():
    return _load_json(THEME_FILE).get("default", {})


def _verify_admin(creds: HTTPBasicCredentials = Depends(security)):
    correct_user = secrets.compare_digest(creds.username, ADMIN_USER)
    correct_pw = secrets.compare_digest(creds.password, ADMIN_PASS)
    if not (correct_user and correct_pw):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    return True


@router.post("/update/{client}", summary="Update a client's customization (admin)")
async def update_customization(client: str, payload: Dict[str, Any], _a: bool = Depends(_verify_admin)):
    data = _load_json(CUSTOM_FILE)
    data[client] = payload
    with open(CUSTOM_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return {"status": "ok", "client": client}


@router.post("/theme/update", summary="Update default theme (admin)")
async def update_theme(payload: Dict[str, Any], _a: bool = Depends(_verify_admin)):
    data = _load_json(THEME_FILE)
    data["default"] = payload
    with open(THEME_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    return {"status": "ok"}
