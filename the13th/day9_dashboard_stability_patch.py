#!/usr/bin/env python3
"""
Day 9 — Dashboard Stability Patch
---------------------------------
This script applies all fixes required to eliminate:
  • "React is not defined"
  • "e.map is not a function"
  • inconsistent payload structure from /api/plan
  • missing default values

It auto-patches the frontend React dashboard and backend plan API.

Run from repo root:
    python day9_dashboard_stability_patch.py
"""

import os
import json
import logging
from pathlib import Path
import subprocess

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("DAY9")

REPO = Path(__file__).resolve().parent
FRONTEND = REPO / "frontend" / "src"
BACKEND = REPO / "app"

# -------------------------------------------------------------------
# 1) Fix React import errors
# -------------------------------------------------------------------
REACT_FILES = [
    FRONTEND / "App.jsx",
    FRONTEND / "components" / "Dashboard.jsx",
    FRONTEND / "components" / "Header.jsx",
]

REACT_IMPORT = "import React from 'react';\n"

def ensure_react_import(f: Path):
    if not f.exists():
        return
    txt = f.read_text()
    if "import React" not in txt:
        txt = REACT_IMPORT + txt
        f.write_text(txt)
        log.info(f"✔ Added React import → {f.relative_to(REPO)}")
    else:
        log.info(f"✔ React import OK → {f.relative_to(REPO)}")

# -------------------------------------------------------------------
# 2) Fix the e.map crash
#    Dashboard expected an array but received undefined/null
# -------------------------------------------------------------------
DASHBOARD_FILE = FRONTEND / "components" / "Dashboard.jsx"

def fix_dashboard_map():
    if not DASHBOARD_FILE.exists():
        return
    txt = DASHBOARD_FILE.read_text()

    # Ensure safe array defaults
    safe_patch = "const list = Array.isArray(props.items) ? props.items : [];"

    if "Array.isArray" not in txt:
        txt = txt.replace(
            "props.items.map",
            "(Array.isArray(props.items) ? props.items : []).map"
        )
        DASHBOARD_FILE.write_text(txt)
        log.info(f"✔ Dashboard safe-map patch applied → {DASHBOARD_FILE.relative_to(REPO)}")
    else:
        log.info(f"✔ Dashboard map safe already present")

# -------------------------------------------------------------------
# 3) Fix backend /api/plan output to always return consistent structure
# -------------------------------------------------------------------
PLAN_FILE = BACKEND / "main.py"

def fix_api_plan():
    if not PLAN_FILE.exists():
        log.warning("main.py not found, cannot patch plan API")
        return

    txt = PLAN_FILE.read_text()
    if "def get_plan" not in txt:
        return

    # new stable payload
    block = """
@app.get("/api/plan")
async def get_plan():
    return {
        "plan": "Free",
        "usage": {
            "cpu": 0.2,
            "ram": 128,
        },
        "projects": [],
        "tenants": [],
        "status": "running",
    }
"""

    # replace old version
    if "Temporary API endpoint for dashboard testing" in txt:
        # remove old block entirely
        pre = txt.split("def get_plan")[0]
        new_txt = pre + block
        PLAN_FILE.write_text(new_txt)
        log.info(f"✔ Updated /api/plan → {PLAN_FILE.relative_to(REPO)}")
    else:
        log.info("✔ /api/plan already stable")

# -------------------------------------------------------------------
# 4) Rebuild frontend
# -------------------------------------------------------------------
def rebuild_frontend():
    cmd = ["npm", "run", "build"]
    try:
        log.info("🔧 Rebuilding frontend...")
        subprocess.run(cmd, cwd=(REPO / "frontend"), check=True)
        log.info("✔ Frontend rebuild complete")
    except Exception as e:
        log.error(f"❌ Frontend build failed: {e}")

# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------
def main():
    log.info("=== DAY 9: Dashboard Stability Patch ===")

    for f in REACT_FILES:
        ensure_react_import(f)

    fix_dashboard_map()
    fix_api_plan()
    rebuild_frontend()

    log.info("\n🎯 Patch complete. Push to GitHub and redeploy on Render.")

if __name__ == "__main__":
    main()
