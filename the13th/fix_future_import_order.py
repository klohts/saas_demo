#!/usr/bin/env python3
"""
Fixes SyntaxError: from __future__ imports must occur at the beginning of the file
in app_intelligence_app.py by reordering imports correctly.
"""
from pathlib import Path
import shutil
from datetime import datetime
import logging
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("fix_future_import_order")

base = Path(__file__).resolve().parent
target = base / "app_intelligence" / "app_intelligence_app.py"
backup_dir = base / "patch_backups"
backup_dir.mkdir(exist_ok=True)
timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
backup = backup_dir / f"app_intelligence_app.py.bak.{timestamp}"
shutil.copy(target, backup)
log.info(f"📦 Backup created at {backup}")

code = target.read_text().splitlines()

# Remove misplaced __future__ imports
future_lines = [line for line in code if line.strip().startswith("from __future__ import")]
code = [line for line in code if not line.strip().startswith("from __future__ import")]

# Reinsert correctly at very top
final_code = "\n".join(future_lines + [""] + code)
target.write_text(final_code)
log.info("✅ __future__ import moved to the top of the file.")

log.info("🎯 Now restart App Intelligence:")
log.info("   cd app_intelligence && source .venv/bin/activate && python app_intelligence_app.py")
