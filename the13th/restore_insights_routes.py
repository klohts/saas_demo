#!/usr/bin/env python3
"""
Restores /api/insights/recent and /api/insights/summary endpoints
to THE13TH App Intelligence service.
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import shutil
import logging
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("restore_routes")

BASE = Path(__file__).resolve().parent
TARGET = BASE / "app_intelligence" / "app_intelligence_app.py"
BACKUP_DIR = BASE / "patch_backups"
BACKUP_DIR.mkdir(exist_ok=True)

timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
backup = BACKUP_DIR / f"app_intelligence_app.py.bak.{timestamp}"
shutil.copy(TARGET, backup)
log.info(f"📦 Backup created at {backup}")

code = TARGET.read_text()

# Check if routes exist
if "/api/insights/recent" in code:
    log.info("✅ Insights routes already present — nothing to do.")
    exit(0)

# Find a good place to inject (after app = FastAPI(...))
inject_anchor = "app = FastAPI"
snippet = """
# --- Insights Endpoints Re-Added ---

@app.get("/api/insights/recent", tags=["insights"])
def get_recent_insights(limit: int = 20):
    with Session(engine) as session:
        events = session.exec(select(Event).order_by(Event.created_at.desc()).limit(limit)).all()
        return {"events": [e.dict() for e in events]}

@app.get("/api/insights/summary", tags=["insights"])
def get_summary():
    with Session(engine) as session:
        total = session.exec(select(func.count(Event.id))).one()
        clients = session.exec(select(func.count(func.distinct(Event.client_id)))).one()
        actions = session.exec(select(func.count(func.distinct(Event.action)))).one()
        return {
            "summary": {
                "total_events": total,
                "unique_clients": clients,
                "unique_actions": actions,
            }
        }

# --- End of Insights Endpoints ---
"""

if inject_anchor in code:
    code = re.sub(rf"({inject_anchor}.*\n)", r"\1" + snippet + "\n", code, count=1)
else:
    code += snippet

# Ensure missing imports
imports = "\n".join([
    "from sqlmodel import Session, select, func",
])
if "from sqlmodel import Session" not in code:
    code = imports + "\n" + code

TARGET.write_text(code)
log.info("✅ Insights routes successfully restored.")

log.info("🎯 Restart the App Intelligence service:")
log.info("   cd app_intelligence && source .venv/bin/activate && python app_intelligence_app.py")
