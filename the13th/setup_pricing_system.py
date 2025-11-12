#!/usr/bin/env python3
"""
setup_pricing_system.py

Creates a 3-tier pricing configuration and lightweight Pricing microservice + frontend pricing page
for THE13TH project. This is a single, idempotent script that writes files into the the13th repo and
updates the frontend App.jsx where possible.

Files created/modified by this script (exact locations):
- ./config/pricing.json
- ./pricing_service/pricing_service.py
- ./pricing_service/.env.example
- ./pricing_service/requirements.txt
- ./pricing_service/Dockerfile
- ./intelligence_dashboard/src/pages/Pricing.jsx
- ./intelligence_dashboard/src/components/PricingCard.jsx
- ./intelligence_dashboard/src/styles.css (appends minimal pricing styles)
- ./README_PRICING.md

HOW TO RUN (from project root: ~/AIAutomationProjects/saas_demo/the13th):
1) python setup_pricing_system.py
2) Start the pricing microservice (separate from existing services):
   cd pricing_service && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
   export PRICING_CONFIG=$(pwd)/../config/pricing.json && python pricing_service.py

3) Frontend: rebuild intelligence_dashboard if using Vite:
   cd intelligence_dashboard && npm install && npm run build (or run dev server)
   then copy dist to app_intelligence/dist if required.

Notes:
- The pricing microservice listens on PORT (default 8003). It serves GET /api/pricing.
- The script attempts to insert a /pricing route into intelligence_dashboard/src/App.jsx when a React Router
  Routes block is detected. If not detected, it leaves files in place and prints a next-step.

"""
from __future__ import annotations
import os
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("setup_pricing")

ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "config"
PRICING_PATH = CONFIG_DIR / "pricing.json"
PRICING_SERVICE_DIR = ROOT / "pricing_service"
FRONTEND_PAGES = ROOT / "intelligence_dashboard" / "src" / "pages"
FRONTEND_COMPONENTS = ROOT / "intelligence_dashboard" / "src" / "components"
FRONTEND_STYLES = ROOT / "intelligence_dashboard" / "src" / "styles.css"
APP_JSX = ROOT / "intelligence_dashboard" / "src" / "App.jsx"
README = ROOT / "README_PRICING.md"

# --- Ensure directories ---
for d in (CONFIG_DIR, PRICING_SERVICE_DIR, FRONTEND_PAGES, FRONTEND_COMPONENTS):
    d.mkdir(parents=True, exist_ok=True)

# --- 1) pricing.json ---
pricing_default = {
    "version": "1.0",
    "currency": "USD",
    "tiers": [
        {
            "id": "basic",
            "name": "Basic",
            "price_monthly": 29,
            "limits": {"dashboards": 1, "alerts": 50},
            "description": "Good for solo agents and testing."
        },
        {
            "id": "pro",
            "name": "Pro",
            "price_monthly": 199,
            "limits": {"dashboards": 5, "alerts": 1000},
            "description": "Most teams will start here."
        },
        {
            "id": "enterprise",
            "name": "Enterprise",
            "price_monthly": 899,
            "limits": {"dashboards": 50, "alerts": 100000},
            "description": "Dedicated support and SSO."
        }
    ],
    "notes": "IDs are stable identifiers used by checkout integration."
}

if not PRICING_PATH.exists():
    PRICING_PATH.write_text(json.dumps(pricing_default, indent=2))
    log.info(f"✅ Created pricing config: {PRICING_PATH}")
else:
    # ensure version present; merge basic keys if missing
    try:
        existing = json.loads(PRICING_PATH.read_text())
        if existing.get("version") != pricing_default["version"]:
            existing["version"] = pricing_default["version"]
            PRICING_PATH.write_text(json.dumps(existing, indent=2))
            log.info(f"🔧 Updated pricing config version at: {PRICING_PATH}")
        else:
            log.info(f"ℹ️ Pricing config already exists at: {PRICING_PATH}")
    except Exception:
        PRICING_PATH.write_text(json.dumps(pricing_default, indent=2))
        log.info(f"✅ Rewrote pricing config (was corrupted): {PRICING_PATH}")

# --- 2) pricing_service.py ---
PRICING_SERVICE_APP = PRICING_SERVICE_DIR / "pricing_service.py"
PRICING_SERVICE_ENV = PRICING_SERVICE_DIR / ".env.example"
PRICING_REQUIREMENTS = PRICING_SERVICE_DIR / "requirements.txt"
PRICING_DOCKER = PRICING_SERVICE_DIR / "Dockerfile"

pricing_service_code = f'''#!/usr/bin/env python3
from __future__ import annotations
import os
import json
import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from starlette.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("pricing_service")

PRICING_CONFIG = Path(os.getenv('PRICING_CONFIG', '{PRICING_PATH.as_posix()}'))
API_KEY = os.getenv('PRICING_API_KEY', '')
PORT = int(os.getenv('PORT', '8003'))

app = FastAPI(title="THE13TH — Pricing Service", version="1.0.0")

class Tier(BaseModel):
    id: str
    name: str
    price_monthly: float
    limits: dict
    description: Optional[str]

class PricingResponse(BaseModel):
    version: str
    currency: str
    tiers: list[Tier]


def load_pricing() -> dict:
    if not PRICING_CONFIG.exists():
        log.error('Pricing config not found at %s', PRICING_CONFIG)
        raise FileNotFoundError('pricing config not found')
    with PRICING_CONFIG.open() as f:
        return json.load(f)


@app.get('/api/pricing', response_model=PricingResponse)
def get_pricing(x_api_key: Optional[str] = Header(None)):
    """
    Return pricing config. If PRICING_API_KEY is set, require it in X-API-KEY header.
    """
    if API_KEY:
        if not x_api_key or x_api_key != API_KEY:
            raise HTTPException(status_code=401, detail='Invalid API Key')
    try:
        data = load_pricing()
        return JSONResponse(content=data)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail='Pricing config missing')


if __name__ == '__main__':
    import uvicorn
    log.info('Starting Pricing Service on port %s — serving %s', PORT, PRICING_CONFIG)
    uvicorn.run('pricing_service:app', host='0.0.0.0', port=PORT, reload=False)
'''
if not PRICING_SERVICE_APP.exists():
    PRICING_SERVICE_APP.write_text(pricing_service_code)
    os.chmod(PRICING_SERVICE_APP, 0o755)
    log.info(f"✅ Created pricing service app: {PRICING_SERVICE_APP}")
else:
    log.info(f"ℹ️ Pricing service app already exists: {PRICING_SERVICE_APP}")

PRICING_SERVICE_ENV.write_text("PRICING_CONFIG=../config/pricing.json\n#PRICING_API_KEY=your-api-key\n#PORT=8003\n")
PRICING_REQUIREMENTS.write_text("fastapi\nuvicorn[standard]\npython-dotenv\n")
PRICING_DOCKER.write_text("""FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python","pricing_service.py"]
""")
log.info(f"✅ Wrote pricing service helper files to: {PRICING_SERVICE_DIR}")

# --- 3) Frontend Pricing page (React) ---
PRICING_PAGE = FRONTEND_PAGES / "Pricing.jsx"
PRICING_CARD = FRONTEND_COMPONENTS / "PricingCard.jsx"

pricing_card_code = """import React from 'react'

export default function PricingCard({tier}){
  return (
    <div className="card pricing-card">
      <h3 className="header">{tier.name}</h3>
      <p className="muted">{tier.description}</p>
      <div className="price">${tier.price_monthly}/mo</div>
      <ul>
        {Object.entries(tier.limits || {}).map(([k,v])=>(<li key={k}>{k}: {v}</li>))}
      </ul>
      <button className="btn">Select</button>
    </div>
  )
}
"""

pricing_page_code = """import React, {useEffect, useState} from 'react'
import PricingCard from '../components/PricingCard'

export default function Pricing(){
  const [pricing, setPricing] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(()=>{
    fetch('/api/pricing')
      .then(r=>{ if(!r.ok) throw new Error('Pricing fetch failed'); return r.json() })
      .then(setPricing)
      .catch(e=>setErr(e.message))
  },[])

  if(err) return <div className="card"><h3>Error</h3><p>{err}</p></div>
  if(!pricing) return <div className="card">Loading...</div>

  return (
    <div className="page container">
      <h1 className="header">Pricing</h1>
      <div className="pricing-grid">
        {pricing.tiers.map(t => <PricingCard key={t.id} tier={t} />)}
      </div>
    </div>
  )
}
"""

# write files (idempotent)
if not PRICING_CARD.exists():
    PRICING_CARD.write_text(pricing_card_code)
    log.info(f"✅ Created frontend component: {PRICING_CARD}")
else:
    log.info(f"ℹ️ Frontend component already exists: {PRICING_CARD}")

if not PRICING_PAGE.exists():
    PRICING_PAGE.write_text(pricing_page_code)
    log.info(f"✅ Created frontend page: {PRICING_PAGE}")
else:
    log.info(f"ℹ️ Frontend page already exists: {PRICING_PAGE}")

# append minimal styles if not present
styles_snippet = "\n/* Pricing styles (appended by setup_pricing_system.py) */\n.pricing-grid { display:flex; gap:12px; flex-wrap:wrap; }\n.pricing-card { width:260px; }\n.price { font-size:1.5rem; font-weight:700; margin:8px 0; }\n.btn { background: #6b21a8; color:white; padding:8px 12px; border-radius:8px; border:none; }\n"
if FRONTEND_STYLES.exists():
    content = FRONTEND_STYLES.read_text()
    if 'Pricing styles (appended by setup_pricing_system.py)' not in content:
        FRONTEND_STYLES.write_text(content + styles_snippet)
        log.info(f"✅ Appended pricing styles to: {FRONTEND_STYLES}")
    else:
        log.info(f"ℹ️ Pricing styles already present in: {FRONTEND_STYLES}")
else:
    FRONTEND_STYLES.write_text(styles_snippet)
    log.info(f"✅ Created styles file: {FRONTEND_STYLES}")

# --- 4) Try to inject route into App.jsx ---
if APP_JSX.exists():
    app_text = APP_JSX.read_text()
    if '/pricing' in app_text:
        log.info(f"ℹ️ App.jsx already contains /pricing route.")
    else:
        # attempt to detect <Routes> block and insert Route
        if 'Routes' in app_text and 'Route' in app_text:
            # naive insertion: find first occurrence of <Routes> and insert a Route after it
            new_text = app_text.replace('<Routes>', '<Routes>\n        <Route path="/pricing" element={<Pricing/>} />')
            # ensure import for Pricing exists
            if "import Pricing from './pages/Pricing'" not in new_text:
                new_text = new_text.replace("import ", "import Pricing from './pages/Pricing'\nimport ", 1)
            APP_JSX.write_text(new_text)
            log.info(f"✅ Injected /pricing route into: {APP_JSX}")
        else:
            log.warning("⚠️ Could not detect Routes block inside %s. Please add a Route manually:\n <Route path=\"/pricing\" element={<Pricing />} />\n and import Pricing from './pages/Pricing'." % APP_JSX)
else:
    log.warning(f"⚠️ Could not find App.jsx at {APP_JSX}. Frontend route not injected.")

# --- 5) README ---
README.write_text(f"""
THE13TH Pricing System — created {datetime.utcnow().isoformat()}Z

Files created/modified (exact paths):
- {PRICING_PATH}
- {PRICING_SERVICE_APP}
- {PRICING_SERVICE_ENV}
- {PRICING_REQUIREMENTS}
- {PRICING_DOCKER}
- {PRICING_CARD}
- {PRICING_PAGE}
- {FRONTEND_STYLES} (appended)

Run the pricing microservice (recommended):
  cd {PRICING_SERVICE_DIR}
  python -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  export PRICING_CONFIG={PRICING_PATH}
  python pricing_service.py

Once running you can test:
  curl http://localhost:8003/api/pricing

If you serve frontend via app_intelligence, ensure the frontend dev server or build publishes /api/pricing proxy or the pricing service is reachable from the frontend (CORS or reverse-proxy).""")
log.info(f"✅ Wrote README: {README}")

log.info("🎉 Setup complete. Verify files and run pricing_service as instructed.")
