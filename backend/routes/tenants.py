from fastapi import APIRouter, HTTPException
from backend.core.tenants import get_tenant_manager
from backend.utils.demo_engine import DemoEngine
import os, logging
from pydantic import BaseModel
from typing import Dict

logger = logging.getLogger("routes.tenants")
router = APIRouter(tags=["tenants"])

tm = get_tenant_manager()
_demo = DemoEngine(interval=int(os.getenv("DEMO_EVENT_INTERVAL","10")), enabled=os.getenv("DEMO_ENABLED","1")=="1")

class TenantPatch(BaseModel):
    name: str
    theme: Dict[str,str] = {}
    logo: str = ""
    demo: bool = True

@router.get("/tenant/list")
def list_tenants():
    return {"tenants": tm.list_tenants()}

@router.get("/tenant/{slug}")
def get_tenant(slug:str):
    t = tm.get(slug)
    if not t: raise HTTPException(status_code=404, detail="Not found")
    return t

@router.post("/tenant/{slug}")
def upsert(slug:str, cfg:TenantPatch):
    tm.add_or_update(slug, cfg.dict())
    return {"status":"ok","tenant":cfg.dict()}

@router.post("/demo/toggle")
def toggle_demo(enabled: bool):
    if enabled: _demo.start()
    else: _demo.stop()
    return {"demo_enabled": enabled}

@router.get("/demo/status")
def demo_status():
    running = _demo._thread and _demo._thread.is_alive()
    return {"running": bool(running), "interval": _demo.interval}
