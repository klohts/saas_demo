#!/usr/bin/env python3
"""
setup_event_relay_patch.py
------------------------------------
Prepares the distributed event relay patch between:
 - THE13TH Control Core (port 8021)
 - THE13TH App Intelligence (port 8011)

This script only validates and generates the patch files;
no modifications are applied until you manually execute it.
"""

import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path
import requests

# --------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
CONTROL_CORE = BASE_DIR / "control_core" / "control_core_app.py"
APP_INTELLIGENCE = BASE_DIR / "app_intelligence" / "app_intelligence_app.py"
BACKUP_DIR = BASE_DIR / "relay_patch_backups"
BACKUP_DIR.mkdir(exist_ok=True)

SERVICES = {
    "client_customization": "http://localhost:8001/healthz",
    "app_intelligence": "http://localhost:8011/healthz",
    "control_core": "http://localhost:8021/healthz",
}

logger = logging.getLogger("relay_patch")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------
def health_check(url: str, retries: int = 3, delay: int = 1) -> bool:
    for _ in range(retries):
        try:
            r = requests.get(url, timeout=3)
            if r.ok:
                return True
        except requests.RequestException:
            time.sleep(delay)
    return False


def backup_file(path: Path):
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_path = BACKUP_DIR / f"{path.name}.bak.{timestamp}"
    backup_path.write_text(path.read_text())
    logger.info(f"🔹 Backup created: {backup_path}")
    return backup_path


def insert_patch_marker(target: Path, marker: str, code_block: str):
    text = target.read_text()
    if marker in text:
        logger.warning(f"⚠️ Marker already exists in {target.name}, skipping insertion.")
        return False
    text += f"\n\n# === {marker} ===\n{code_block.strip()}\n# === END {marker} ===\n"
    target.write_text(text)
    return True


# --------------------------------------------------------------------
# Relay Patch Code Snippets
# --------------------------------------------------------------------

CONTROL_CORE_PATCH = r"""
# === Event Relay Patch (AUTO-GENERATED) ===
import threading
import queue
import requests

_relay_queue = queue.Queue()
_last_ack = None

def _relay_worker():
    global _last_ack
    while True:
        event = _relay_queue.get()
        if event is None:
            break
        try:
            r = requests.post(
                "http://localhost:8011/api/relay/receive",
                json=event,
                timeout=5
            )
            if r.ok:
                _last_ack = datetime.utcnow().isoformat()
                logger.info(f"✅ Relayed event {event.get('action')} to App Intelligence.")
            else:
                logger.warning(f"⚠️ Relay failed: {r.status_code} {r.text}")
        except Exception as e:
            logger.error(f"❌ Relay exception: {e}")
        _relay_queue.task_done()

# start background worker thread
threading.Thread(target=_relay_worker, daemon=True).start()
# === END Event Relay Patch ===
"""

APP_INTELLIGENCE_PATCH = r"""
# === Relay Receiver Patch (AUTO-GENERATED) ===
from fastapi import Request

@app.post("/api/relay/receive")
async def receive_relay(request: Request):
    try:
        payload = await request.json()
        logger.info(f"📩 Received relayed event: {payload.get('action')} from {payload.get('client_id')}")
        return {"status": "ack", "received_at": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"❌ Failed to handle relay event: {e}")
        return {"status": "error", "detail": str(e)}
# === END Relay Receiver Patch ===
"""

# --------------------------------------------------------------------
# Run Preflight Validation
# --------------------------------------------------------------------
logger.info("🚦 Checking service health...")

health_results = {svc: health_check(url) for svc, url in SERVICES.items()}
for svc, ok in health_results.items():
    logger.info(f"{svc:<22} → {'✅ OK' if ok else '❌ DOWN'}")

if not all(health_results.values()):
    logger.error("❌ One or more services are offline. Please start all before patching.")
    raise SystemExit(1)

logger.info("✅ All services online. Preparing patch...")

# --------------------------------------------------------------------
# Backup and Prepare Patch
# --------------------------------------------------------------------
backup_file(CONTROL_CORE)
backup_file(APP_INTELLIGENCE)

PREVIEW_FILE = BASE_DIR / "relay_patch_preview.json"
preview_data = {
    "timestamp": datetime.utcnow().isoformat(),
    "control_core_patch_snippet": CONTROL_CORE_PATCH.strip().splitlines()[:6],
    "app_intelligence_patch_snippet": APP_INTELLIGENCE_PATCH.strip().splitlines()[:6],
}
PREVIEW_FILE.write_text(json.dumps(preview_data, indent=2))

logger.info(f"🧩 Patch snippets prepared (preview saved at {PREVIEW_FILE}).")
logger.info("No code has been modified yet — safe to review.")

print(
    "\n✅ Relay patch ready.\n\n"
    "Next steps:\n"
    "  1️⃣ Review the patch preview: cat relay_patch_preview.json\n"
    "  2️⃣ Apply manually when ready:\n"
    "       python setup_event_relay_patch.py --apply\n"
    "  3️⃣ Restart all services.\n"
)
