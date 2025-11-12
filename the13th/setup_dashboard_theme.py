#!/usr/bin/env python3
"""
setup_dashboard_theme.py — fixed Tailwind literal braces

Overwrites THE13TH Intelligence Dashboard with grey (#f9fafb) and purple (#7c3aed) theme,
then rebuilds and copies dist/ to app_intelligence/dist/ safely.
"""
from __future__ import annotations
import os, sys, shutil, subprocess, json, logging
from pathlib import Path
from datetime import datetime
from typing import Tuple

ROOT = Path('/home/hp/AIAutomationProjects/saas_demo/the13th')
FRONTEND = ROOT / 'intelligence_dashboard'
BACKEND_DIST = ROOT / 'app_intelligence' / 'dist'
BACKUP_DIR = ROOT / 'backups'
THEME_PURPLE = '#7c3aed'
BG_GREY = '#f9fafb'
NODE_TIMEOUT = 1800

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('setup_dashboard_theme')

FILES_TO_OVERWRITE = {
    'tailwind.config.cjs': f"""module.exports = {{
  content: [ './index.html', './src/**/*.{{
    js,jsx,ts,tsx
  }}' ],
  theme: {{
    extend: {{
      colors: {{
        primary: '{THEME_PURPLE}',
        background: '{BG_GREY}'
      }}
    }}
  }},
  plugins: [],
}};
""",

    'postcss.config.cjs': """module.exports = { plugins: { tailwindcss: {}, autoprefixer: {}, } };
""",

    'src/styles.css': f"""@tailwind base;
@tailwind components;
@tailwind utilities;

:root {{ --bg: {BG_GREY}; --primary: {THEME_PURPLE}; }}
body {{ background: var(--bg); font-family: ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; color: #374151; }}
.card {{ background: white; border-radius: 12px; box-shadow: 0 6px 18px rgba(15,23,42,0.06); padding: 16px; }}
.header {{ color: var(--primary); font-weight: 600; }}
.table {{ width: 100%; border-collapse: collapse; }}
.table th, .table td {{ padding: 8px 10px; border-bottom: 1px solid #e6e6e6; }}
""",

    'src/App.jsx': """import React, { useEffect, useState } from 'react';
import axios from 'axios';
import Stats from './components/Stats';
import Events from './components/Events';
import './styles.css';
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';
export default function App(){
  const [summary, setSummary] = useState(null);
  const [events, setEvents] = useState([]);
  useEffect(()=>{ fetchSummary(); fetchEvents(); }, []);
  async function fetchSummary(){ try{ const r = await axios.get(`${API_BASE}/api/insights/summary`, { headers: { 'X-SYS-API-KEY': 'supersecret_sys_key' }}); setSummary(r.data); }catch(e){ console.error(e); } }
  async function fetchEvents(){ try{ const r = await axios.get(`${API_BASE}/api/insights/recent?limit=50`, { headers: { 'X-SYS-API-KEY': 'supersecret_sys_key' }}); setEvents(r.data.events); }catch(e){ console.error(e); } }
  return (<div className='p-8'><h1 className='text-3xl mb-6 header'>THE13TH Intelligence Dashboard</h1><Stats data={summary} /><div className='mt-6 card'><Events events={events} /></div></div>);
}
""",

    'src/components/Stats.jsx': """import React from 'react';
export default function Stats({data}){
  if(!data) return <div className='card'>Loading summary...</div>;
  return (<div className='grid grid-cols-3 gap-4'>
    <div className='card'><div className='text-sm'>Total Events</div><div className='text-2xl header'>{data.total_events}</div></div>
    <div className='card'><div className='text-sm'>Unique Clients</div><div className='text-2xl header'>{data.unique_clients}</div></div>
    <div className='card'><div className='text-sm'>Top Action</div><div className='text-2xl header'>{data.top_actions?.[0]?.action || '-'}</div></div>
  </div>);
}
""",

    'src/components/Events.jsx': """import React from 'react';
export default function Events({events}){
  return (<div><h2 className='text-xl mb-2 header'>Recent Events</h2><table className='table'><thead><tr><th>Time</th><th>Client</th><th>Action</th><th>User</th></tr></thead><tbody>{events.map(e=>(<tr key={e.id}><td>{new Date(e.created_at).toLocaleString()}</td><td>{e.client_id}</td><td>{e.action}</td><td>{e.user}</td></tr>))}</tbody></table></div>);
}
""",
}


def run(cmd: str, cwd: Path | None = None, timeout: int = NODE_TIMEOUT) -> Tuple[int, str, str]:
    proc = subprocess.Popen(cmd, shell=True, cwd=str(cwd) if cwd else None,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        return 1, out, f'Timeout after {timeout}s\n{err}'
    return proc.returncode, out, err


def backup_and_overwrite():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    fe_backup = FRONTEND.parent / f"intelligence_dashboard.bak.{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"
    shutil.copytree(FRONTEND, fe_backup)
    if BACKEND_DIST.exists():
        bd_backup = BACKEND_DIST.parent / f"dist.bak.{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"
        shutil.copytree(BACKEND_DIST, bd_backup)
    for rel, content in FILES_TO_OVERWRITE.items():
        target = FRONTEND / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        logger.info("Wrote %s", target)


def rebuild():
    rc, out, err = run('npm install', cwd=FRONTEND)
    if rc != 0:
        raise SystemExit(err or out)
    rc, out, err = run('npm run build', cwd=FRONTEND)
    if rc != 0:
        raise SystemExit(err or out)
    dist_src = FRONTEND / 'dist'
    if BACKEND_DIST.exists():
        shutil.rmtree(BACKEND_DIST)
    shutil.copytree(dist_src, BACKEND_DIST)


def main():
    logger.info('Starting THE13TH dashboard theme update')
    backup_and_overwrite()
    rebuild()
    logger.info('✅ Dashboard theme updated successfully. Visit http://localhost:8011/dashboard')


if __name__ == '__main__':
    main()
