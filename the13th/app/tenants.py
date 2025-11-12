from __future__ import annotations

import os
import json
import sqlite3
import secrets
from pathlib import Path
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

# --------------------------------------
# Database + Config paths (always absolute)
# --------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "tenants.db"
CONFIG_ROOT = BASE_DIR / "config" / "tenants"

router = APIRouter(tags=["Tenants"])


# --------------------------------------
# DB Helpers
# --------------------------------------
def get_conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# --------------------------------------
# Models
# --------------------------------------
class TenantCreate(BaseModel):
    name: str


class TenantOut(BaseModel):
    id: str
    name: str
    api_key: str
    config_path: str
    created_at: str


# --------------------------------------
# Create Tenant
# --------------------------------------
@router.post("/", response_model=TenantOut, status_code=201)
async def create_tenant(payload: TenantCreate):
    tenant_id = secrets.token_urlsafe(8)
    api_key = secrets.token_urlsafe(32)
    created_at = datetime.now(timezone.utc).isoformat()

    tenant_dir = CONFIG_ROOT / tenant_id
    tenant_dir.mkdir(parents=True, exist_ok=True)

    config_path = tenant_dir / "customization.json"
    config_path.write_text(json.dumps({
        "tenant_id": tenant_id,
        "name": payload.name,
        "theme": {"primary": "#4F46E5", "accent": "#06B6D4"},
        "branding": {"logo": "", "company": payload.name},
    }, indent=2))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tenants (id, name, api_key, config_path, created_at) VALUES (?, ?, ?, ?, ?)",
        (tenant_id, payload.name, api_key, str(config_path), created_at),
    )
    conn.commit()
    conn.close()

    return TenantOut(
        id=tenant_id,
        name=payload.name,
        api_key=api_key,
        config_path=str(config_path),
        created_at=created_at,
    )


# --------------------------------------
# List Tenants
# --------------------------------------
@router.get("/", response_model=List[TenantOut])
async def list_tenants():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, name, api_key, config_path, created_at FROM tenants ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    return [
        TenantOut(
            id=row["id"],
            name=row["name"],
            api_key=row["api_key"],
            config_path=row["config_path"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


# --------------------------------------
# Get Single Tenant
# --------------------------------------
@router.get("/{tenant_id}", response_model=TenantOut)
async def get_tenant(tenant_id: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, name, api_key, config_path, created_at FROM tenants WHERE id = ?",
        (tenant_id,)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Tenant not found")

    return TenantOut(
        id=row["id"],
        name=row["name"],
        api_key=row["api_key"],
        config_path=row["config_path"],
        created_at=row["created_at"],
    )
