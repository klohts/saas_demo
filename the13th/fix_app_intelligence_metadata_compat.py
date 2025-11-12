#!/usr/bin/env python3
"""
Patch App Intelligence to accept both `metadata` and `details` in incoming events,
but store only `details` in the database.
"""

from __future__ import annotations
import shutil
from datetime import datetime
from pathlib import Path
import logging
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("fix_metadata_compat")

BASE = Path(__file__).resolve().parent
TARGET = BASE / "app_intelligence" / "app_intelligence_app.py"
BACKUP_DIR = BASE / "patch_backups"
BACKUP_DIR.mkdir(exist_ok=True)

timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
backup_path = BACKUP_DIR / f"app_intelligence_app.py.bak.{timestamp}"
shutil.copy(TARGET, backup_path)
log.info(f"📦 Backup created at {backup_path}")

text = TARGET.read_text()

# --- 1. Update Pydantic model to handle both metadata/details ---
if "class EventIn(" in text:
    text = re.sub(
        r"class EventIn\(BaseModel\):[\s\S]+?(\n\n|\Z)",
        """
class EventIn(BaseModel):
    client_id: str
    action: str
    user: str
    details: Optional[dict] = None
    metadata: Optional[dict] = None

    @root_validator(pre=True)
    def unify_metadata(cls, values):
        if "metadata" in values and "details" not in values:
            values["details"] = values.pop("metadata")
        return values
""",
        text,
    )

# --- 2. Update insert logic (use .details not .metadata) ---
text = re.sub(r"new_event\s*=\s*Event\([^)]*\)", 
              "new_event = Event(client_id=payload.client_id, action=payload.action, user=payload.user, details=payload.details, timestamp=payload.timestamp or datetime.utcnow().isoformat())", 
              text)

TARGET.write_text(text)
log.info("✅ Added backward compatibility for metadata → details mapping")

log.info("🎯 Restart App Intelligence service:")
log.info("   cd app_intelligence && source .venv/bin/activate && python app_intelligence_app.py")
