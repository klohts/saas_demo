#!/usr/bin/env python3
"""
Final patch to ensure App Intelligence Event model schema uses 'details' JSON column.
"""

from __future__ import annotations
import shutil
from datetime import datetime
from pathlib import Path
import re
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("fix_event_model")

BASE = Path(__file__).resolve().parent
TARGET = BASE / "app_intelligence" / "app_intelligence_app.py"
BACKUP_DIR = BASE / "patch_backups"
BACKUP_DIR.mkdir(exist_ok=True)

timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
backup_path = BACKUP_DIR / f"app_intelligence_app.py.bak.{timestamp}"
shutil.copy(TARGET, backup_path)
log.info(f"📦 Backup created at {backup_path}")

text = TARGET.read_text()

# --- 1. Replace SQLModel Event definition ---
text = re.sub(
    r"class Event\(SQLModel, table=True\):[\s\S]+?class",
    """class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: str
    action: str
    user: str
    details: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    timestamp: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def dict(self, *args, **kwargs):
        data = super().dict(*args, **kwargs)
        if "details" not in data:
            data["details"] = {}
        return data

class """,
    text,
)

# --- 2. Ensure SQLAlchemy imports exist ---
if "from sqlalchemy import Column, JSON" not in text:
    text = text.replace("from sqlmodel import", "from sqlalchemy import Column, JSON\nfrom sqlmodel import")

# --- 3. Update all old references to metadata ---
text = text.replace(".metadata", ".details")
text = re.sub(r"\bmetadata\b", "details", text)

# --- 4. Save changes ---
TARGET.write_text(text)
log.info("✅ Updated SQLModel Event schema to use 'details' column.")

# --- 5. Reset old DB to rebuild ---
db_file = BASE / "app_intelligence" / "data" / "events.db"
if db_file.exists():
    db_file.unlink()
    log.info(f"🗑️  Removed old DB: {db_file}")

log.info("🎯 Restart App Intelligence to rebuild schema:")
log.info("   cd app_intelligence && source .venv/bin/activate && python app_intelligence_app.py")
