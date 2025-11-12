# File: ~/AIAutomationProjects/saas_demo/the13th/setup_unified_event_bus.py
"""
THE13TH — Unified Event Bus + Persistent Metrics Core
-----------------------------------------------------
This script:
  • Connects Control Core → App Intelligence → Client Customization.
  • Adds persistent metrics tracking (total events, unique clients, uptime).
  • Registers /api/system/overview on Control Core for real-time aggregation.
  • Verifies all 3 health endpoints before wiring up.
"""

import os
import json
import time
import logging
import requests 
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any


BASE_DIR = Path(__file__).resolve().parent
CONTROL_DIR = BASE_DIR / "control_core"
CONTROL_APP = CONTROL_DIR / "control_core_app.py"

CC_URLS = {
    "client_customization": "http://localhost:8001/healthz",
    "app_intelligence": "http://localhost:8011/healthz",
    "control_core": "http://localhost:8021/healthz",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("unified_bus_setup")

# ------------------------------------------------------------
# 1️⃣ Validate all services are healthy
# ------------------------------------------------------------
def check_health():
    healthy = {}
    for name, url in CC_URLS.items():
        try:
            res = requests.get(url, timeout=3)
            healthy[name] = res.status_code == 200
            log.info(f"{name} → {'✅ OK' if healthy[name] else '❌ Fail'}")
        except Exception as e:
            healthy[name] = False
            log.error(f"{name} → ❌ {e}")
    if not all(healthy.values()):
        raise SystemExit("❌ One or more services are not healthy.")
    log.info("All services healthy. Proceeding...")

# ------------------------------------------------------------
# 2️⃣ Patch Control Core for persistent metrics + system overview
# ------------------------------------------------------------
def patch_control_core():
    if not CONTROL_APP.exists():
        raise FileNotFoundError(f"Missing file: {CONTROL_APP}")

    original = CONTROL_APP.read_text().splitlines()
    backup_path = CONTROL_DIR / f"control_core_app.py.bak.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    backup_path.write_text("\n".join(original))
    log.info(f"Backup created at {backup_path}")

    # Skip if already patched
    if any("def system_overview" in line for line in original):
        log.warning("System overview already present — skipping re-patch.")
        return

    injection = [
        "",
        "# --- Unified Event Bus + System Overview Patch ---",
        "from fastapi import Depends",
        "import threading, sqlite3",
        "",
        "# Persistent metrics store",
        "METRICS_DB = Path(__file__).parent / 'data' / 'metrics.db'",
        "METRICS_DB.parent.mkdir(parents=True, exist_ok=True)",
        "",
        "def init_metrics():",
        "    with sqlite3.connect(METRICS_DB) as db:",
        "        db.execute('''CREATE TABLE IF NOT EXISTS metrics (key TEXT PRIMARY KEY, value INTEGER)''')",
        "        db.execute('''INSERT OR IGNORE INTO metrics (key, value) VALUES ('total_events', 0)''')",
        "        db.execute('''INSERT OR IGNORE INTO metrics (key, value) VALUES ('unique_clients', 0)''')",
        "        db.commit()",
        "",
        "def update_metric(key: str, delta: int = 1):",
        "    with sqlite3.connect(METRICS_DB) as db:",
        "        db.execute('UPDATE metrics SET value = value + ? WHERE key = ?', (delta, key))",
        "        db.commit()",
        "",
        "def get_metrics():",
        "    with sqlite3.connect(METRICS_DB) as db:",
        "        return dict(db.execute('SELECT key, value FROM metrics').fetchall())",
        "",
        "@app.post('/api/events', tags=['events'])",
        "async def unified_ingest(event: dict):",
        "    import aiohttp",
        "    update_metric('total_events', 1)",
        "    client_id = event.get('client_id')",
        "    if client_id:",
        "        update_metric('unique_clients', 1)",
        "    # Relay to intelligence service",
        "    AI_URL = os.getenv('CC_APP_INTELLIGENCE_URL', 'http://localhost:8011/api/events')",
        "    async with aiohttp.ClientSession() as session:",
        "        try:",
        "            async with session.post(AI_URL, json=event, timeout=5) as resp:",
        "                log.info(f'Relayed event to App Intelligence → {resp.status}')",
        "        except Exception as e:",
        "            log.error(f'Failed to relay event → {e}')",
        "    return {'status': 'queued', 'event': event}",
        "",
        "@app.get('/api/system/overview', tags=['system'])",
        "def system_overview():",
        "    try:",
        "        cc = requests.get('http://localhost:8001/healthz').json()",
        "        ai = requests.get('http://localhost:8011/healthz').json()",
        "        ctrl = requests.get('http://localhost:8021/healthz').json()",
        "        metrics = get_metrics()",
        "        return {",
        "            'timestamp': datetime.now(timezone.utc).isoformat(),",
        "            'services': {'client_customization': cc, 'app_intelligence': ai, 'control_core': ctrl},",
        "            'metrics': metrics",
        "        }",
        "    except Exception as e:",
        "        return {'detail': str(e)}",
        "",
        "@app.on_event('startup')",
        "def _init_metrics():",
        "    init_metrics()",
        "    log.info('✅ Metrics DB initialized.')",
        "# --- End Patch ---",
        "",
    ]

    # Insert before the final line
    CONTROL_APP.write_text("\n".join(original + injection))
    log.info(f"Patched Control Core with unified event bus + metrics.")

# ------------------------------------------------------------
# 3️⃣ Run checks + patch
# ------------------------------------------------------------
if __name__ == "__main__":
    check_health()
    patch_control_core()
    log.info("✅ Unified Event Bus successfully integrated.")
    print("\n🎯 Next steps:")
    print("  1. Restart Control Core:")
    print("       cd ~/AIAutomationProjects/saas_demo/the13th/control_core")
    print("       source .venv/bin/activate && python control_core_app.py")
    print("  2. Test system overview endpoint:")
    print("       curl -s http://localhost:8021/api/system/overview | jq")
    print("  3. Fire an event:")
    print("       curl -X POST http://localhost:8021/api/events -H 'Content-Type: application/json' -d '{\"client_id\":\"agent001\",\"action\":\"dashboard_test\"}'")
