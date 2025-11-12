#!/usr/bin/env python3
"""
setup_dashboard_layout.py — aligns and spaces THE13TH dashboard without changing logic.
"""
from __future__ import annotations
import shutil, subprocess, logging
from pathlib import Path
from datetime import datetime

ROOT = Path("/home/hp/AIAutomationProjects/saas_demo/the13th")
FRONTEND = ROOT / "intelligence_dashboard"
BACKEND_DIST = ROOT / "app_intelligence" / "dist"
BACKUP_DIR = ROOT / "backups"
THEME_PURPLE = "#7c3aed"
BG_GREY = "#f9fafb"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("setup_dashboard_layout")

FILES = {
    "src/styles.css": f"""@tailwind base;
@tailwind components;
@tailwind utilities;

:root {{
  --bg: {BG_GREY};
  --primary: {THEME_PURPLE};
}}

body {{
  background: var(--bg);
  color: #374151;
  font-family: ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;
  display: flex;
  justify-content: center;
  padding: 40px 20px;
}}

.container {{
  width: 100%;
  max-width: 1100px;
}}

.header {{
  color: var(--primary);
  font-weight: 700;
  margin-bottom: 24px;
}}

.card {{
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  padding: 20px;
  margin-bottom: 20px;
}}

.grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}}

.table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}}

.table th {{
  text-align: left;
  padding: 10px;
  background: #f3f4f6;
  color: #4b5563;
  font-weight: 600;
}}

.table td {{
  padding: 10px;
  border-bottom: 1px solid #e5e7eb;
}}

.table tr:hover {{
  background: #fafafa;
}}
""",

    "src/App.jsx": """import React, { useEffect, useState } from 'react';
import axios from 'axios';
import Stats from './components/Stats';
import Events from './components/Events';
import './styles.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export default function App() {
  const [summary, setSummary] = useState(null);
  const [events, setEvents] = useState([]);

  useEffect(() => {
    fetchSummary();
    fetchEvents();
  }, []);

  async function fetchSummary() {
    try {
      const r = await axios.get(`${API_BASE}/api/insights/summary`, {
        headers: { 'X-SYS-API-KEY': 'supersecret_sys_key' }
      });
      setSummary(r.data);
    } catch (e) { console.error(e); }
  }

  async function fetchEvents() {
    try {
      const r = await axios.get(`${API_BASE}/api/insights/recent?limit=50`, {
        headers: { 'X-SYS-API-KEY': 'supersecret_sys_key' }
      });
      setEvents(r.data.events);
    } catch (e) { console.error(e); }
  }

  return (
    <div className="container">
      <h1 className="text-3xl header">THE13TH Intelligence Dashboard</h1>
      <Stats data={summary} />
      <div className="card">
        <Events events={events} />
      </div>
    </div>
  );
}
"""
}


def backup():
    BACKUP_DIR.mkdir(exist_ok=True)
    backup_dir = FRONTEND.parent / f"intelligence_dashboard.layout.bak.{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"
    shutil.copytree(FRONTEND, backup_dir)
    log.info(f"📦 Backup created at {backup_dir}")


def rebuild():
    subprocess.run("npm install", cwd=FRONTEND, shell=True, check=True)
    subprocess.run("npm run build", cwd=FRONTEND, shell=True, check=True)
    dist_src = FRONTEND / "dist"
    if BACKEND_DIST.exists():
        shutil.rmtree(BACKEND_DIST)
    shutil.copytree(dist_src, BACKEND_DIST)
    log.info("✅ Build complete and synced to backend dist/")


def main():
    backup()
    for rel, content in FILES.items():
        f = FRONTEND / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(content)
        log.info(f"✏️ Updated {f}")
    rebuild()
    log.info("🎯 Layout refined. Visit http://localhost:8011/dashboard")


if __name__ == "__main__":
    main()
