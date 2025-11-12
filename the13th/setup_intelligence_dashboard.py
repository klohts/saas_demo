#!/usr/bin/env python3
"""
Setup script — THE13TH Event Intelligence Dashboard (Phase 2)

This single script will:
- Update the App Intelligence backend to add a summary endpoint and serve a React dashboard.
- Create a frontend React + Vite + Tailwind app under:
  /home/hp/AIAutomationProjects/saas_demo/the13th/intelligence_dashboard/
- Write an upgraded backend file at:
  /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/app_intelligence_app.py
  (this file will mount the built frontend at /dashboard and serve /api/insights/summary)

Run once:
  python3 setup_intelligence_dashboard.py

Then build & run:
  cd /home/hp/AIAutomationProjects/saas_demo/the13th/intelligence_dashboard
  # install node deps (requires node+npm)
  npm install
  npm run build

  # backend venv
  cd /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  # ensure .env example contains THE13TH_SYS_KEY and AI_DATABASE_URL
  cp .env.example .env
  export $(cat .env | xargs)
  python app_intelligence_app.py

Open dashboard at: http://localhost:8011/dashboard

"""
from pathlib import Path
import json

ROOT = Path('/home/hp/AIAutomationProjects/saas_demo/the13th')
APP_INTEL = ROOT / 'app_intelligence'
FRONTEND = ROOT / 'intelligence_dashboard'

for d in [APP_INTEL, FRONTEND]:
    d.mkdir(parents=True, exist_ok=True)

def write(p: Path, s: str, binary: bool=False):
    p.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        p.write_bytes(s)
    else:
        p.write_text(s.strip()+"\n")
    print('✅', p)

# 1) Overwrite backend: app_intelligence_app.py (mount static, add /api/insights/summary)
backend_code = r'''#!/usr/bin/env python3
# File: /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/app_intelligence_app.py
"""
App Intelligence Engine (upgraded: Phase 2)
- Serves static React dashboard at /dashboard
- Adds /api/insights/summary for dashboard metrics
- Uses SQLite (AI_DATABASE_URL) and THE13TH_SYS_KEY for system auth
"""
from __future__ import annotations
import os, sys, logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / '.env.example', override=True)

from fastapi import FastAPI, Request, Header, HTTPException, status
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlmodel import SQLModel, Field as ORMField, create_engine, Session, select, func

# config
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv('AI_DATABASE_URL', f"sqlite:///{DATA_DIR / 'events.db'}")
THE13TH_SYS_KEY = os.getenv('THE13TH_SYS_KEY', 'sys-default-key')
PORT = int(os.getenv('PORT', '8011'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('app_intelligence')

# models
class Event(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = ORMField(default=None, primary_key=True)
    client_id: Optional[str] = ORMField(index=True, nullable=True)
    action: str = ORMField(nullable=False)
    user: Optional[str] = None
    meta_json: Optional[str] = None
    created_at: datetime = ORMField(default_factory=datetime.utcnow)

class EventCreate(BaseModel):
    client_id: Optional[str] = Field(None)
    action: str = Field(..., min_length=1)
    user: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

# db
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {})

def init_db():
    SQLModel.metadata.create_all(engine)
    logger.info('Initialized DB at %s', DATABASE_URL)

def get_session():
    return Session(engine)

# app
app = FastAPI(title='THE13TH App Intelligence', version='2.0')

# mount static if build exists
FRONTEND_DIST = BASE_DIR.parent / 'intelligence_dashboard' / 'dist'
if FRONTEND_DIST.exists():
    app.mount('/dashboard', StaticFiles(directory=str(FRONTEND_DIST), html=True), name='dashboard')

# simple sys key check
async def require_sys_key(x_sys_api_key: Optional[str] = Header(None)) -> None:
    if x_sys_api_key is None or x_sys_api_key != THE13TH_SYS_KEY:
        logger.warning('Invalid system API key attempt')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid system API key')

@app.on_event('startup')
def on_startup():
    init_db()

@app.post('/api/events')
def ingest_event(payload: EventCreate, x_sys_api_key: Optional[str] = Header(None)):
    if x_sys_api_key is None or x_sys_api_key != THE13TH_SYS_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid system API key')
    import json
    meta_str = json.dumps(payload.metadata or {})
    ev = Event(client_id=payload.client_id, action=payload.action, user=payload.user, meta_json=meta_str)
    with get_session() as sess:
        sess.add(ev)
        sess.commit()
        sess.refresh(ev)
    logger.info('Ingested event id=%s action=%s client=%s', ev.id, ev.action, ev.client_id)
    return JSONResponse(status_code=201, content={'id': ev.id, 'created_at': ev.created_at.isoformat()})

@app.get('/api/insights/recent')
def recent_events(limit: int = 20, x_sys_api_key: Optional[str] = Header(None)):
    if x_sys_api_key is None or x_sys_api_key != THE13TH_SYS_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid system API key')
    limit = max(1, min(100, limit))
    with get_session() as sess:
        q = select(Event).order_by(Event.created_at.desc()).limit(limit)
        rows = sess.exec(q).all()
        import json
        out = []
        for r in rows:
            out.append({'id': r.id, 'client_id': r.client_id, 'action': r.action, 'user': r.user, 'metadata': json.loads(r.meta_json) if r.meta_json else {}, 'created_at': r.created_at.isoformat()})
    return JSONResponse(content={'events': out})

@app.get('/api/insights/summary')
def insights_summary(x_sys_api_key: Optional[str] = Header(None)):
    if x_sys_api_key is None or x_sys_api_key != THE13TH_SYS_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid system API key')
    with get_session() as sess:
        total = sess.exec(select(func.count()).select_from(Event)).one()
        unique_clients = sess.exec(select(func.count(func.distinct(Event.client_id)))).one()
        # top actions
        rows = sess.exec(select(Event.action, func.count().label('cnt')).group_by(Event.action).order_by(func.count().desc()).limit(10)).all()
        top_actions = [{'action': r[0], 'count': int(r[1])} for r in rows]
        # recent users
        users = sess.exec(select(func.distinct(Event.user)).order_by(Event.created_at.desc()).limit(10)).all()
        recent_users = [u[0] for u in users if u[0]]
    return JSONResponse(content={'total_events': int(total), 'unique_clients': int(unique_clients), 'top_actions': top_actions, 'recent_users': recent_users})

@app.get('/healthz')
def healthz():
    return {'status': 'ok', 'app': 'THE13TH App Intelligence'}

# serve dashboard index if mounted and no path
@app.get('/dashboard', include_in_schema=False)
def dashboard_index():
    index_file = FRONTEND_DIST / 'index.html'
    if index_file.exists():
        return FileResponse(str(index_file))
    raise HTTPException(status_code=404, detail='Dashboard not built')

if __name__ == '__main__':
    import uvicorn
    init_db()
    uvicorn.run('app_intelligence_app:app', host='0.0.0.0', port=PORT)
'''

write(APP_INTEL / 'app_intelligence_app.py', backend_code)

# 2) Frontend: Vite React app (lightweight)
# package.json
package_json = {
  'name': 'the13th-intelligence-dashboard',
  'version': '0.1.0',
  'private': True,
  'scripts': {
    'dev': 'vite',
    'build': 'vite build && cp -r dist ../app_intelligence/dist',
    'preview': 'vite preview'
  },
  'dependencies': {
    'react': '^18.2.0',
    'react-dom': '^18.2.0',
    'axios': '^1.4.0',
    'recharts': '^2.6.2'
  },
  'devDependencies': {
    'vite': '^5.0.0',
    'tailwindcss': '^3.5.0',
    'postcss': '^8.4.0',
    'autoprefixer': '^10.4.0'
  }
}
write(FRONTEND / 'package.json', json.dumps(package_json, indent=2))

# vite config
vite_config = r"""import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: { outDir: 'dist' },
  server: { port: 8012 }
})
"""
write(FRONTEND / 'vite.config.js', vite_config)

# index.html
index_html = r"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>THE13TH Intelligence Dashboard</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""
write(FRONTEND / 'index.html', index_html)

# tailwind config
tailwind = r"""module.exports = {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: { extend: {} },
  plugins: [],
}
"""
write(FRONTEND / 'tailwind.config.cjs', tailwind)

# postcss
postcss = r"""module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  }
}
"""
write(FRONTEND / 'postcss.config.cjs', postcss)

# src files
src_main = r"""import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles.css'

createRoot(document.getElementById('root')).render(<App />)
"""
write(FRONTEND / 'src' / 'main.jsx', src_main)

src_app = r"""import React, { useEffect, useState } from 'react'
import axios from 'axios'
import Stats from './components/Stats'
import Events from './components/Events'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

export default function App(){
  const [summary, setSummary] = useState(null)
  const [events, setEvents] = useState([])

  useEffect(()=>{ fetchSummary(); fetchEvents(); }, [])

  async function fetchSummary(){
    try{
      const r = await axios.get(`${API_BASE}/api/insights/summary`, { headers: { 'X-SYS-API-KEY': 'supersecret_sys_key' }})
      setSummary(r.data)
    }catch(e){ console.error(e) }
  }
  async function fetchEvents(){
    try{
      const r = await axios.get(`${API_BASE}/api/insights/recent?limit=50`, { headers: { 'X-SYS-API-KEY': 'supersecret_sys_key' }})
      setEvents(r.data.events)
    }catch(e){ console.error(e) }
  }

  return (
    <div className="p-6 font-sans">
      <h1 className="text-2xl mb-4">THE13TH Intelligence Dashboard</h1>
      <Stats data={summary} />
      <Events events={events} />
    </div>
  )
}
"""
write(FRONTEND / 'src' / 'App.jsx', src_app)

# components
write(FRONTEND / 'src' / 'components' / 'Stats.jsx', r"""import React from 'react'
export default function Stats({data}){
  if(!data) return <div>Loading summary...</div>
  return (
    <div className="grid grid-cols-3 gap-4 mb-6">
      <div className="p-4 border rounded">Total Events<br/><strong>{data.total_events}</strong></div>
      <div className="p-4 border rounded">Unique Clients<br/><strong>{data.unique_clients}</strong></div>
      <div className="p-4 border rounded">Top Action<br/><strong>{data.top_actions?.[0]?.action || '-'}</strong></div>
    </div>
  )
}
""")

write(FRONTEND / 'src' / 'components' / 'Events.jsx', r"""import React from 'react'
export default function Events({events}){
  return (
    <div>
      <h2 className="text-xl mb-2">Recent Events</h2>
      <table className="min-w-full border-collapse">
        <thead><tr><th className="border p-2">Time</th><th className="border p-2">Client</th><th className="border p-2">Action</th><th className="border p-2">User</th></tr></thead>
        <tbody>
          {events.map(e=> (
            <tr key={e.id}><td className="border p-2">{new Date(e.created_at).toLocaleString()}</td><td className="border p-2">{e.client_id}</td><td className="border p-2">{e.action}</td><td className="border p-2">{e.user}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
""")

# styles
write(FRONTEND / 'src' / 'styles.css', r"""@tailwind base;@tailwind components;@tailwind utilities;body{font-family:ui-sans-serif,system-ui,-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial}
""")

# env for frontend
write(FRONTEND / '.env', 'VITE_API_BASE_URL=http://localhost:8011')

# README for frontend
write(FRONTEND / 'README.md', """# THE13TH Intelligence Dashboard (frontend)

Install and build:

```bash
cd /home/hp/AIAutomationProjects/saas_demo/the13th/intelligence_dashboard
npm install
npm run build
```

The build copies the static files into `/home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence/dist` and the backend serves them at `/dashboard`.
""")

print('\n🎯 Intelligence Dashboard scaffolding complete.')
print('Next steps:')
print('  1) Build frontend:')
print('     cd /home/hp/AIAutomationProjects/saas_demo/the13th/intelligence_dashboard')
print('     npm install')
print('     npm run build')
print('  2) Start backend:')
print('     cd /home/hp/AIAutomationProjects/saas_demo/the13th/app_intelligence')
print('     python -m venv .venv && source .venv/bin/activate')
print('     pip install -r requirements.txt')
print('     cp .env.example .env && export $(cat .env | xargs)')
print('     python app_intelligence_app.py')
print('\nOpen http://localhost:8011/dashboard')
