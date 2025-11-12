"""
FastAPI router for tenant onboarding (auto-generated).
Mount in your main app with: `from app.tenants import router as tenants_router` then
`app.include_router(tenants_router, prefix="/api/tenants")`.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict
from datetime import datetime, timezone
import secrets
import json
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

DB_PATH = Path(r"/home/hp/AIAutomationProjects/saas_demo/the13th/data/tenants.db")
CONFIG_ROOT = Path("/home/hp/AIAutomationProjects/saas_demo/the13th/config/tenants")

router = APIRouter(tags=["tenants"])


class TenantCreate(BaseModel):
    name: str


class TenantOut(BaseModel):
    id: str
    name: str
    api_key: str
    config_path: str
    created_at: str


def _get_conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    return conn


@router.post("/", response_model=TenantOut, status_code=201)
async def create_tenant(payload: TenantCreate):
    """Create a tenant, generate API key, create config folder and persist to SQLite."""
    tenant_id = secrets.token_urlsafe(8)
    api_key = secrets.token_urlsafe(32)
    created_at = datetime.now(timezone.utc).isoformat()
    tenant_dir = CONFIG_ROOT / tenant_id
    tenant_dir.mkdir(parents=True, exist_ok=True)
    customization = {
        "tenant_id": tenant_id,
        "name": payload.name,
        "theme": {"primary": "#4F46E5", "accent": "#06B6D4"},
        "branding": {"logo": "", "company": payload.name},
    }
    config_path = tenant_dir / "customization.json"
    config_path.write_text(json.dumps(customization, indent=2))

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tenants (id, name, api_key, config_path, created_at) VALUES (?, ?, ?, ?, ?)",
            (tenant_id, payload.name, api_key, str(config_path), created_at),
        )
        conn.commit()
    finally:
        conn.close()

    return TenantOut(id=tenant_id, name=payload.name, api_key=api_key, config_path=str(config_path), created_at=created_at)


@router.get("/", response_model=list[TenantOut])
async def list_tenants():
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, api_key, config_path, created_at FROM tenants ORDER BY created_at DESC")
        rows = cur.fetchall()
        return [TenantOut(id=r[0], name=r[1], api_key=r[2], config_path=r[3], created_at=r[4]) for r in rows]
    finally:
        conn.close()


@router.get("/{tenant_id}", response_model=TenantOut)
async def get_tenant(tenant_id: str):
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, api_key, config_path, created_at FROM tenants WHERE id = ?", (tenant_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
        return TenantOut(id=row[0], name=row[1], api_key=row[2], config_path=row[3], created_at=row[4])
    finally:
        conn.close()
