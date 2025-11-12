from fastapi import APIRouter, HTTPException
import sqlite3, os
from pydantic import BaseModel
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "../data/tenants.db")
router = APIRouter(prefix="/api/tenants", tags=["Tenants"])

class TenantUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    logo_url: str | None = None
    tagline: str | None = None

def db_conn():
    return sqlite3.connect(DB_PATH)

@router.get("/{tenant_id}")
def get_tenant(tenant_id: int):
    con = db_conn(); cur = con.cursor()
    cur.execute("SELECT id, name, color, logo_url, tagline, created_at FROM tenants WHERE id=?", (tenant_id,))
    row = cur.fetchone(); con.close()
    if not row:
        raise HTTPException(status_code=404, detail="Tenant not found")
    keys = ["id","name","color","logo_url","tagline","created_at"]
    return dict(zip(keys, row))

@router.put("/{tenant_id}")
def update_tenant(tenant_id: int, data: TenantUpdate):
    con = db_conn(); cur = con.cursor()
    cur.execute("SELECT id FROM tenants WHERE id=?", (tenant_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Tenant not found")
    for field, value in data.dict(exclude_unset=True).items():
        cur.execute(f"UPDATE tenants SET {field}=? WHERE id=?", (value, tenant_id))
    con.commit(); con.close()
    return {"status":"updated","tenant_id":tenant_id,"fields":data.dict(exclude_unset=True)}
