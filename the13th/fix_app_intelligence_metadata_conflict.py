#!/usr/bin/env python3
"""
Auto-fix for reserved field 'metadata' conflict in App Intelligence Event model.
"""

from __future__ import annotations
import shutil
from datetime import datetime
from pathlib import Path
import re
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("fix_metadata_conflict")

BASE = Path(__file__).resolve().parent
APP_FILE = BASE / "app_intelligence" / "app_intelligence_app.py"
BACKUP_DIR = BASE / "patch_backups"
BACKUP_DIR.mkdir(exist_ok=True)

timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
backup_path = BACKUP_DIR / f"app_intelligence_app.py.bak.{timestamp}"
shutil.copy(APP_FILE, backup_path)
log.info(f"📦 Backup created at {backup_path}")

text = APP_FILE.read_text()

# Replace metadata field definition
text = re.sub(
    r"metadata\s*:\s*Optional\[dict\].*",
    "details: Optional[dict] = Field(default=None, sa_column=Column(JSON))",
    text,
)

# Replace all other references to .metadata
text = re.sub(r"\.metadata", ".details", text)

# Ensure imports
if "from sqlalchemy import Column, JSON" not in text:
    text = text.replace("from sqlmodel import", "from sqlalchemy import Column, JSON\nfrom sqlmodel import")

APP_FILE.write_text(text)
log.info(f"✅ Updated Event model to use 'details' instead of 'metadata'")

# Delete old DB to rebuild schema cleanly
db_file = BASE / "app_intelligence" / "data" / "events.db"
if db_file.exists():
    db_file.unlink()
    log.info(f"🗑️  Removed old DB at {db_file}")

log.info("🎯 Done. Now restart App Intelligence:")
log.info("   cd app_intelligence && source .venv/bin/activate && python app_intelligence_app.py")
