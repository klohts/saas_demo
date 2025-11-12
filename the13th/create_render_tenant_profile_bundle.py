#!/usr/bin/env python3
# ============================================
# Day 9: Tenant Profiles & Brand Customization Bundle — THE13TH
# ============================================
# Purpose: Per-tenant branding (color, logo, tagline) + profile UI
# Auto-creates backend routes, React component, git commit, Render deploy
# ============================================

import os, sqlite3, subprocess, json, logging, requests
from datetime import datetime
from pathlib import Path

# --------------------------------------------
# Config
# --------------------------------------------
REPO = Path(__file__).resolve().parent
APP_DIR = REPO / "app"
FRONTEND = REPO / "frontend" / "src"
COMPONENTS = FRONTEND / "components"
DEPLOY_HOOK = "https://api.render.com/deploy/srv-d4a6l07gi27c739spc0g?key=ZBnxoh-Us8o"
TENANTS_DB = REPO / "data" / "tenants.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("Day9TenantProfiles")

# --------------------------------------------
# 1️⃣ Backend routes (extend tenants API)
# --------------------------------------------
router_path = APP_DIR / "tenant_profiles.py"
router_code = """from fastapi import APIRouter, HTTPException
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
"""
router_path.write_text(router_code)
log.info(f"✅ Created backend router {router_path}")

# --------------------------------------------
# 2️⃣ Update SQLite schema if needed
# --------------------------------------------
TENANTS_DB.parent.mkdir(parents=True, exist_ok=True)
con = sqlite3.connect(TENANTS_DB)
con.execute("""CREATE TABLE IF NOT EXISTS tenants(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT,
  color TEXT DEFAULT '#2563eb',
  logo_url TEXT,
  tagline TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
)""")
con.commit(); con.close()
log.info(f"✅ Ensured tenants.db schema at {TENANTS_DB}")

# --------------------------------------------
# 3️⃣ React component: TenantProfile.jsx
# --------------------------------------------
COMPONENTS.mkdir(parents=True, exist_ok=True)
profile_path = COMPONENTS / "TenantProfile.jsx"
profile_code = """import React, { useEffect, useState } from "react";

export default function TenantProfile({ tenantId, onClose }) {
  const [tenant, setTenant] = useState(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});

  const fetchTenant = async () => {
    const res = await fetch(`/api/tenants/${tenantId}`);
    if (res.ok) setTenant(await res.json());
  };

  const saveTenant = async () => {
    const res = await fetch(`/api/tenants/${tenantId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    if (res.ok) {
      setEditing(false);
      await fetchTenant();
    }
  };

  useEffect(() => { fetchTenant(); }, [tenantId]);

  if (!tenant) return <div className="p-4">Loading...</div>;

  return (
    <div className="p-6 bg-white rounded-2xl shadow-md mt-6 border border-gray-200">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-gray-800">Tenant Profile</h2>
        <button onClick={onClose} className="text-sm text-gray-500 hover:text-gray-700">✕ Close</button>
      </div>

      <div className="flex items-center gap-4 mb-4">
        {tenant.logo_url && <img src={tenant.logo_url} alt="Logo" className="w-16 h-16 rounded-lg" />}
        <div>
          <h3 className="text-xl font-semibold" style={{color: tenant.color || '#2563eb'}}>{tenant.name}</h3>
          <p className="text-gray-600">{tenant.tagline || "No tagline yet"}</p>
        </div>
      </div>

      {editing ? (
        <div className="space-y-3">
          <input className="border px-3 py-2 w-full" placeholder="Name"
            defaultValue={tenant.name} onChange={e=>setForm({...form, name:e.target.value})}/>
          <input className="border px-3 py-2 w-full" placeholder="Logo URL"
            defaultValue={tenant.logo_url} onChange={e=>setForm({...form, logo_url:e.target.value})}/>
          <input className="border px-3 py-2 w-full" placeholder="Color"
            defaultValue={tenant.color} onChange={e=>setForm({...form, color:e.target.value})}/>
          <input className="border px-3 py-2 w-full" placeholder="Tagline"
            defaultValue={tenant.tagline} onChange={e=>setForm({...form, tagline:e.target.value})}/>
          <button onClick={saveTenant} className="bg-blue-600 text-white px-4 py-2 rounded-lg">Save</button>
        </div>
      ) : (
        <button onClick={()=>setEditing(true)} className="bg-blue-600 text-white px-4 py-2 rounded-lg">Edit</button>
      )}
    </div>
  );
}
"""
profile_path.write_text(profile_code)
log.info(f"✅ Created {profile_path}")

# --------------------------------------------
# 4️⃣ Patch App.jsx (link to TenantProfile)
# --------------------------------------------
appjsx = FRONTEND / "App.jsx"
if appjsx.exists():
    text = appjsx.read_text()
    if "TenantProfile" not in text:
        injected = (
            'import TenantProfile from "./components/TenantProfile";\n'
            'import AdminTenantPanel from "./components/AdminTenantPanel";\n\n'
            "export default function App(){\n"
            "  const [selectedTenant,setSelectedTenant]=React.useState(null);\n"
            "  return (<div className='p-8'>\n"
            "  {!selectedTenant && <AdminTenantPanel onSelect={setSelectedTenant}/>}\n"
            "  {selectedTenant && <TenantProfile tenantId={selectedTenant.id} onClose={()=>setSelectedTenant(null)}/>}\n"
            "  </div>);}"
        )
        appjsx.write_text(injected)
        log.info(f"✅ Injected TenantProfile view into App.jsx")
else:
    log.warning("⚠️ App.jsx not found")

# --------------------------------------------
# 5️⃣ Git commit and push
# --------------------------------------------
def git_commit_and_push():
    try:
        subprocess.run(["git","add","."],cwd=REPO,check=True)
        msg=f"chore: Day9 tenant profile & branding bundle — {datetime.utcnow().isoformat()}"
        subprocess.run(["git","commit","-m",msg],cwd=REPO,check=True)
        subprocess.run(["git","push"],cwd=REPO,check=True)
        return True
    except subprocess.CalledProcessError as e:
        log.error(f"Git error: {e}")
        return False

committed = git_commit_and_push()

# --------------------------------------------
# 6️⃣ Trigger Render deploy
# --------------------------------------------
try:
    r=requests.post(DEPLOY_HOOK,timeout=10)
    log.info(f"🚀 Render deploy triggered: {r.text}")
except Exception as e:
    log.error(f"Render trigger failed: {e}")

log.info("🎯 Day9 Tenant Profiles & Branding bundle complete.")
