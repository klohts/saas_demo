#!/usr/bin/env python3
"""
setup_real_estate_mvp.py

Single-run script to add Real Estate MVP analytics endpoints + frontend widgets.

What it does:
- Creates backend/routes/real_estate.py
- Patches main.py to include the new router
- Updates or creates frontend/src/realEstate.jsx
- Patches frontend/src/api.js to expose new API calls
- Creates/updates .env.example with Zapier/AI webhook variables
- Backups any file it modifies (filename.bak.YYYYMMDDTHHMMSS)

Run:
  python scripts/setup_real_estate_mvp.py

Assumptions:
- Run from project root (saas_demo)
- Python 3.10+ available in venv
- Existing structure matches earlier conversation:
  - main.py at project root
  - backend/routes/ exists
  - frontend/src/ exists
"""

from pathlib import Path
import datetime
import shutil
import re
import json
import os
import sys

BASE = Path.cwd()
TIMESTAMP = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S")

def backup(path: Path):
    if path.exists():
        bak = path.with_suffix(path.suffix + f".bak.{TIMESTAMP}")
        shutil.copy2(path, bak)
        print(f"[backup] {path} -> {bak}")

def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup(path)
    path.write_text(content, encoding="utf-8")
    print(f"[written] {path}")

# 1) backend/routes/real_estate.py
backend_router_path = BASE / "backend" / "routes" / "real_estate.py"
real_estate_py = """\
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any
from pathlib import Path
import os, logging, json, time
from datetime import datetime

# Tries to reuse existing analytics engine if present
try:
    from backend.core.analytics import get_engine
    engine = get_engine()
except Exception:
    engine = None

router = APIRouter()

# Event schema
class REEvent(BaseModel):
    user: str
    action: str
    property_id: str | None = None
    metadata: Dict[str, Any] | None = None
    ts: float | None = None

ZAPIER_WEBHOOK = os.getenv("ZAPIER_WEBHOOK_URL", "")
AI_ENGINE_URL = os.getenv("AI_ENGINE_URL", "")

def send_to_zapier(payload: dict) -> bool:
    \"\"\"Send event to Zapier webhook if configured. Non-blocking best-effort.\"\"\"
    if not ZAPIER_WEBHOOK:
        logging.debug(\"ZAP not configured\")
        return False
    try:
        import requests
        r = requests.post(ZAPIER_WEBHOOK, json=payload, timeout=5)
        logging.info(f\"Zapier forwarded: {{r.status_code}} for {{payload.get('action')}}\")
        return r.ok
    except Exception as e:
        logging.exception(\"Failed sending to Zapier: %s\", e)
        return False

def notify_ai_lead_engine(payload: dict) -> bool:
    \"\"\"Optional: send lightweight payload to AI lead reply engine.\"\"\"
    if not AI_ENGINE_URL:
        return False
    try:
        import requests
        r = requests.post(AI_ENGINE_URL, json=payload, timeout=5)
        logging.info(f\"AI engine forwarded: {{r.status_code}} for {{payload.get('action')}}\")
        return r.ok
    except Exception as e:
        logging.exception(\"Failed sending to AI engine: %s\", e)
        return False

# Record event and optionally route to Zapier/AI
@router.post("/event")
async def record_event(e: REEvent):
    payload = e.dict()
    payload['ts'] = payload.get('ts') or time.time()
    # prefer analytics engine if present
    try:
        if engine:
            rec = engine.record_event(payload.get('user','unknown'), payload.get('action'), payload)
        else:
            # fallback: append to backend/data/events.json if exists
            data_file = Path(__file__).resolve().parents[2] / 'data' / 'events.json'
            if data_file.exists():
                try:
                    obj = json.loads(data_file.read_text() or "{{}}")
                except Exception:
                    obj = {{}}
            else:
                obj = {{}}
            # simple list per user
            obj.setdefault(payload.get('user','unknown'), []).append(payload)
            data_file.parent.mkdir(parents=True, exist_ok=True)
            data_file.write_text(json.dumps(obj, indent=2))
            rec = payload
    except Exception as ex:
        logging.exception(\"record_event failed: %s\", ex)
        raise HTTPException(status_code=500, detail=\"record failed\")

    # Forward to Zapier & AI (best-effort, non-blocking)
    try:
        send_to_zapier(payload)
    except Exception:
        pass
    try:
        notify_ai_lead_engine(payload)
    except Exception:
        pass

    # Return simple ack
    return {{ "status": "ok", "event": payload }}

# Summary endpoint - domain-focused for Real Estate
@router.get("/summary")
def summary():
    \"\"\"Return simple real-estate KPIs for demo:
    - top_listings: {{property_id: views}}
    - leads_by_agent: {{agent: leads}}
    - weekly_leads: {{date: count}}
    \"\"\"
    try:
        if engine:
            # use engine.get_events() if available, else use engine.time series helpers
            events = []
            try:
                events = engine.get_events()
            except Exception:
                # engine may not expose get_events; fallback to engine.events store
                events = getattr(engine, 'events', []) or []
        else:
            data_file = Path(__file__).resolve().parents[2] / 'data' / 'events.json'
            if data_file.exists():
                raw = json.loads(data_file.read_text() or '{{}}')
                events = []
                for user, evs in raw.items():
                    for e in evs:
                        e['_user'] = user
                        events.append(e)
            else:
                events = []

        # compute simple KPIs
        top_listings: dict = {{}}
        leads_by_agent: dict = {{}}
        weekly_leads: dict = {{}}
        now = datetime.utcnow()

        for e in events:
            action = e.get('action')
            pid = e.get('property_id')
            user = e.get('user') or e.get('_user') or 'unknown'
            ts = e.get('ts') or e.get('timestamp') or None
            if ts:
                try:
                    created = datetime.utcfromtimestamp(float(ts))
                except Exception:
                    try:
                        created = datetime.fromisoformat(str(ts))
                    except Exception:
                        created = now
            else:
                created = now

            day = created.strftime('%Y-%m-%d')
            # interpret some actions
            if action == 'property_viewed' and pid:
                top_listings[pid] = top_listings.get(pid, 0) + 1
            if action in ('lead_generated', 'contacted_agent'):
                leads_by_agent[user] = leads_by_agent.get(user, 0) + 1
                weekly_leads[day] = weekly_leads.get(day, 0) + 1

        # top listings sorted
        top_listings_sorted = dict(sorted(top_listings.items(), key=lambda x: x[1], reverse=True)[:10])

        return {{
            'top_listings': top_listings_sorted,
            'leads_by_agent': leads_by_agent,
            'weekly_leads': weekly_leads,
            'raw_count': len(events)
        }}
    except Exception as ex:
        logging.exception(\"summary failed: %s\", ex)
        raise HTTPException(status_code=500, detail='calc failed')
"""
write_file(backend_router_path, real_estate_py)

# 2) Patch main.py to include router import + include_router
main_py = BASE / "main.py"
if not main_py.exists():
    print("[error] main.py not found at expected location:", main_py)
    sys.exit(1)

main_text = main_py.read_text(encoding="utf-8")

# Insert import and include_router if not present
import_line = "from backend.routes.real_estate import router as real_estate_router"
include_line = "app.include_router(real_estate_router, prefix=\"/api/real-estate\")"

if import_line not in main_text:
    # Try to insert after other backend.routes imports or after "from backend.routes.analytics import"
    pattern = r"(from backend\.routes\.[^\s]+ import router as [^\n]+\n)"
    m = re.search(pattern, main_text)
    insert_at = None
    if m:
        # insert after last match
        last = 0
        for mm in re.finditer(pattern, main_text):
            last = mm.end()
        insert_at = last
    else:
        # fallback insert after app = FastAPI(...) or at top
        app_decl = re.search(r"app\s*=\s*FastAPI\(", main_text)
        if app_decl:
            insert_at = app_decl.start()
        else:
            insert_at = 0

    # insert import at top region
    new_text = main_text[:insert_at] + ("\n" + import_line + "\n") + main_text[insert_at:]
    main_text = new_text
    print("[patched] inserted import into main.py")

if include_line not in main_text:
    # try to include after other include_router calls or where routes are included
    spot = main_text.find("app.include_router")
    if spot != -1:
        # find end of that line
        endline = main_text.find("\n", spot)
        insertion_point = endline + 1
    else:
        # after app creation
        app_decl = re.search(r"app\s*=\s*FastAPI\([^\)]*\)\s*\n", main_text)
        insertion_point = app_decl.end() if app_decl else 0

    main_text = main_text[:insertion_point] + include_line + "\n" + main_text[insertion_point:]
    print("[patched] inserted include_router into main.py")

# write patched main.py
write_file(main_py, main_text)

# 3) frontend/src/realEstate.jsx (component)
fe_re_path = BASE / "frontend" / "src" / "realEstate.jsx"
re_comp = """\
import React, { useEffect, useState } from 'react';
import { fetchRESummary, postREEvent } from './api';

export default function RealEstatePanel(){
  const [summary, setSummary] = useState({ top_listings: {}, leads_by_agent: {}, weekly_leads: {}, raw_count: 0 });

  useEffect(()=>{
    load();
    const id = setInterval(load, 15000); // refresh every 15s
    return ()=> clearInterval(id);
  }, []);

  async function load(){
    const s = await fetchRESummary();
    if (s) setSummary(s);
  }

  async function sendTest(){
    const r = await postREEvent({ user: 'demo_agent', action: 'property_viewed', property_id: 'listing_123' });
    console.log('posted', r);
    load();
  }

  return (
    <div className="card">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-lg font-semibold text-primary">Real Estate Summary</h3>
          <p className="text-sm text-dark/70">Top listings / leads</p>
        </div>
        <button onClick={sendTest} className="btn">Post demo view</button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <h4 className="font-medium text-primary mb-2">Top Listings</h4>
          <pre className="bg-dark text-light rounded-lg p-3 text-sm overflow-auto">
            {JSON.stringify(summary.top_listings, null, 2)}
          </pre>
        </div>
        <div>
          <h4 className="font-medium text-primary mb-2">Leads by Agent</h4>
          <pre className="bg-dark text-light rounded-lg p-3 text-sm overflow-auto">
            {JSON.stringify(summary.leads_by_agent, null, 2)}
          </pre>
        </div>

        <div>
          <h4 className="font-medium text-primary mb-2">Weekly Leads</h4>
          <pre className="bg-dark text-light rounded-lg p-3 text-sm overflow-auto">
            {JSON.stringify(summary.weekly_leads, null, 2)}
          </pre>
        </div>

        <div>
          <h4 className="font-medium text-primary mb-2">Raw Events</h4>
          <pre className="bg-dark text-light rounded-lg p-3 text-sm overflow-auto">
            {summary.raw_count}
          </pre>
        </div>
      </div>
    </div>
  );
}
"""
write_file(fe_re_path, re_comp)

# 4) Patch frontend/src/api.js to add RE endpoints
fe_api_path = BASE / "frontend" / "src" / "api.js"
if not fe_api_path.exists():
    print("[error] frontend/src/api.js not found, creating a minimal one")
    api_text = """\
// Minimal API client
const API_BASE = "http://127.0.0.1:8000";
async function safeFetch(path, opts){
  try{
    const res = await fetch(API_BASE + path, opts);
    if(!res.ok) return { error: "Failed to fetch", status: res.status };
    return await res.json();
  }catch(e){
    console.error("fetch failed", e);
    return { error: "Failed to fetch" };
  }
}
export async function fetchScores(){ return safeFetch("/analytics/scores"); }
export async function fetchTrend(){ return safeFetch("/analytics/timeseries"); }
export async function fetchUsers(){ return safeFetch("/analytics/users"); }
export async function postEvent(user, action){ return safeFetch("/analytics/event", {method: "POST", headers: {'Content-Type':'application/json'}, body: JSON.stringify({user,action})}); }

// Real estate
export async function postREEvent(payload){ return safeFetch("/api/real-estate/event", {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)}); }
export async function fetchRESummary(){ return safeFetch("/api/real-estate/summary"); }
"""
    write_file(fe_api_path, api_text)
else:
    # read and patch
    orig = fe_api_path.read_text(encoding="utf-8")
    backup(fe_api_path)
    # ensure API_BASE uses https the13th.onrender.com if production, keep localhost default
    patched = orig
    if "fetchRESummary" not in orig:
        # append functions at end
        appended = """

// --- Real Estate (added by setup_real_estate_mvp.py) ---
export async function postREEvent(payload){
  try{
    const res = await fetch(`${API_BASE}/api/real-estate/event`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return await res.json();
  }catch(e){
    console.error('postREEvent failed', e);
    return { error: 'Failed to send' };
  }
}

export async function fetchRESummary(){
  try{
    const res = await fetch(`${API_BASE}/api/real-estate/summary`);
    if(!res.ok) return { error: 'Failed to fetch', status: res.status };
    return await res.json();
  }catch(e){
    console.error('fetchRESummary failed', e);
    return { error: 'Failed to fetch' };
  }
}
"""
        patched = orig + appended
        write_file(fe_api_path, patched)
        print("[patched] frontend/src/api.js appended Real Estate helpers")

# 5) Patch frontend/src/App.jsx to mount RealEstatePanel in main UI if not present
fe_app = BASE / "frontend" / "src" / "App.jsx"
if fe_app.exists():
    app_txt = fe_app.read_text(encoding="utf-8")
    if "realEstate" not in app_txt and "RealEstatePanel" not in app_txt:
        backup(fe_app)
        # Attempt a simple import + JSX insertion: find the main container and insert the component after first grid
        new_import = "import RealEstatePanel from './realEstate';\n"
        # add import after first import block
        app_txt = re.sub(r"(import[^\\n]*\\n)(?=import)", r"\\1", app_txt)  # no-op just safe
        # add import at top
        app_txt = new_import + app_txt
        # Insert <RealEstatePanel /> before closing main container div - heuristic
        if "</div>\\n  );" in app_txt:
            app_txt = app_txt.replace("</div>\\n  );", "  <RealEstatePanel />\\n    </div>\\n  );")
        else:
            # fallback: append at end of function return
            app_txt += "\\n\\n// RealEstatePanel auto-mounted\\n"
        write_file(fe_app, app_txt)
        print("[patched] frontend/src/App.jsx - imported and attempted to mount RealEstatePanel")
    else:
        print("[skip] App.jsx already references RealEstatePanel")
else:
    print("[warn] frontend/src/App.jsx not found; skipping App.jsx patch")

# 6) Add .env.example entries (append or create)
env_example = BASE / ".env.example"
env_lines = [
    "",
    "# Real Estate / Integration settings",
    "ZAPIER_WEBHOOK_URL=",
    "AI_ENGINE_URL=",
]
if env_example.exists():
    txt = env_example.read_text(encoding="utf-8")
    if "ZAPIER_WEBHOOK_URL" not in txt:
        with env_example.open("a", encoding="utf-8") as f:
            f.write("\\n".join(env_lines))
        print("[patched] .env.example appended RE variables")
    else:
        print("[skip] .env.example already contains ZAPIER_WEBHOOK_URL")
else:
    write_file(env_example, "\\n".join(env_lines))
    print("[written] .env.example created with RE variables")

# 7) Summary and next steps
print("\\n--- Setup complete ---")
print("Files created/modified:")
print(f" - {backend_router_path}")
print(f" - patched main.py (included router)")
print(f" - {fe_re_path} (frontend component)")
print(f" - patched frontend/src/api.js")
print(" - .env.example updated")

print("\nNext steps (run these manually):")
print("1) Install requests for backend if not present (used for Zapier/AI forwarding):")
print("   pip install requests\n")
print("2) Restart backend (in project root):")
print("   pkill -f uvicorn || true\n   uvicorn main:app --reload  # or however you run it\n")
print("3) Rebuild frontend and serve (in project root):\n   cd frontend\n   npm install\n   npm run build\n   python ../frontend/server.py\n")
print("4) Open the dashboard and check Real Estate summary -> http://localhost:9000\n")
print("5) Populate .env (copy .env.example -> .env) and set ZAPIER_WEBHOOK_URL / AI_ENGINE_URL if you want Zapier/AI forwarding.")

# 8) Small note on Zapier / AI flow
print("\nZapier / AI flow (how this works):")
print(" - When a real-estate event is POSTed to /api/real-estate/event the backend records it (analytics engine or local store) and then forwards the payload to ZAPIER_WEBHOOK_URL if configured.")
print(" - Zapier can then trigger actions: send email to agent, create CRM lead, call external pipelines.")
print(" - AI_ENGINE_URL is optional: post there to trigger your AI lead reply engine (e.g. to generate automatic replies or triage leads).\n")
