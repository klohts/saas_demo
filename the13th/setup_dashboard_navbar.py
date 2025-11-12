#!/usr/bin/env python3
"""
setup_dashboard_navbar_clean.py — Adds a minimal, centered top navbar for THE13TH Intelligence Dashboard (no clock).
"""
from __future__ import annotations
import shutil, subprocess, logging
from pathlib import Path
from datetime import datetime

ROOT = Path("/home/hp/AIAutomationProjects/saas_demo/the13th")
FRONTEND = ROOT / "intelligence_dashboard"
BACKEND_DIST = ROOT / "app_intelligence" / "dist"
BACKUP_DIR = ROOT / "backups"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("setup_dashboard_navbar_clean")

NAV_CSS = """
.navbar {
  background: white;
  box-shadow: 0 2px 6px rgba(0,0,0,0.04);
  padding: 14px 28px;
  border-radius: 12px;
  display: flex;
  justify-content: flex-start;
  align-items: center;
  margin-bottom: 24px;
}

.nav-title {
  color: var(--primary);
  font-weight: 700;
  font-size: 1.25rem;
  letter-spacing: 0.02em;
}
"""

APP_JSX = """import React, { useEffect, useState } from 'react';
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
      <div className="navbar">
        <div className="nav-title">THE13TH Intelligence Dashboard</div>
      </div>
      <Stats data={summary} />
      <div className="card">
        <Events events={events} />
      </div>
    </div>
  );
}
"""

def backup():
    BACKUP_DIR.mkdir(exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_dir = FRONTEND.parent / f"intelligence_dashboard.navclean.bak.{ts}"
    shutil.copytree(FRONTEND, backup_dir)
    log.info(f"📦 Backup created at {backup_dir}")


def update_files():
    css_file = FRONTEND / "src/styles.css"
    app_file = FRONTEND / "src/App.jsx"

    css_content = css_file.read_text()
    if "navbar" not in css_content:
        css_file.write_text(css_content.strip() + "\n\n" + NAV_CSS)
        log.info("🎨 Updated styles.css with clean navbar styles.")

    app_file.write_text(APP_JSX)
    log.info("✅ Updated App.jsx with clean navbar (no clock).")


def rebuild():
    subprocess.run("npm run build", cwd=FRONTEND, shell=True, check=True)
    dist_src = FRONTEND / "dist"
    if BACKEND_DIST.exists():
        shutil.rmtree(BACKEND_DIST)
    shutil.copytree(dist_src, BACKEND_DIST)
    log.info("📦 Synced new build to backend dist/")


def main():
    backup()
    update_files()
    rebuild()
    log.info("🎯 Clean navbar added successfully. Restart backend and open http://localhost:8011/dashboard")


if __name__ == "__main__":
    main()
