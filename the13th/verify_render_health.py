#!/usr/bin/env python3
"""
verify_render_health.py
---------------------------------
Verifies Render service health by:
1. Checking the latest deploy status via Render API.
2. Waiting for the deploy to become 'live'.
3. Hitting /healthz and / endpoints to ensure app readiness.
"""

import os
import time
import requests
import sys
import logging
from typing import Optional

# --- Configuration ---
RENDER_API_KEY = os.getenv("RENDER_API_KEY", "")
SERVICE_ID = os.getenv("RENDER_SERVICE_ID", "srv-d475kper433s738vdmr0")  # THE13TH
BASE_URL = os.getenv("RENDER_BASE_URL", "https://the13th.onrender.com")
POLL_INTERVAL = 10  # seconds
TIMEOUT = 300  # max seconds to wait

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("verify_render_health")

# --- Helpers ---
def get_latest_deploy_status() -> Optional[str]:
    headers = {"Authorization": f"Bearer {RENDER_API_KEY}"}
    url = f"https://api.render.com/v1/services/{SERVICE_ID}/deploys"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        deploys = r.json()
        if deploys:
            return deploys[0]["status"]
    except Exception as e:
        logger.error(f"Failed to get deploy status: {e}")
    return None


def wait_for_live_status():
    logger.info("Checking Render deploy status...")
    start = time.time()
    while time.time() - start < TIMEOUT:
        status = get_latest_deploy_status()
        if not status:
            logger.warning("No status yet; retrying...")
        elif status.lower() in ("live", "succeeded", "ready"):
            logger.info(f"✅ Deploy is live: {status}")
            return True
        elif status.lower() in ("failed", "cancelled"):
            logger.error(f"❌ Deploy failed: {status}")
            return False
        else:
            logger.info(f"⏳ Current status: {status}")
        time.sleep(POLL_INTERVAL)
    logger.error("❌ Timeout waiting for deploy to go live.")
    return False


def check_endpoint(path: str):
    url = f"{BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            logger.info(f"✅ {path} → OK ({resp.status_code})")
            logger.debug(f"Response: {resp.text[:200]}...")
            return True
        else:
            logger.warning(f"⚠️ {path} → {resp.status_code}")
            logger.debug(resp.text)
            return False
    except Exception as e:
        logger.error(f"❌ Error reaching {path}: {e}")
        return False


def main():
    if not RENDER_API_KEY:
        logger.error("Missing RENDER_API_KEY. Please export it as an environment variable.")
        sys.exit(1)

    if not wait_for_live_status():
        sys.exit(1)

    logger.info("🔍 Verifying health endpoints...")
    ok1 = check_endpoint("/healthz")
    ok2 = check_endpoint("/")

    if ok1 and ok2:
        logger.info("🎉 Service is fully healthy and live!")
        sys.exit(0)
    else:
        logger.warning("⚠️ One or more endpoints failed health check.")
        sys.exit(2)


if __name__ == "__main__":
    main()
