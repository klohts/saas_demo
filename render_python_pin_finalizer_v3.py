#!/usr/bin/env python3
"""
Render Python Pin Finalizer v3 — Hardened Edition
-------------------------------------------------
Automates final Render YAML cleanup, ensures Python version pinning,
commits changes to GitHub, and confirms Render redeploy status safely.
"""

import os
import json
import time
import subprocess
import requests
from pathlib import Path

# === CONFIGURATION ===
PROJECT_DIR = Path("/home/hp/AIAutomationProjects/saas_demo")
RENDER_YAML = Path("/home/hp/AIAutomationProjects/render.yaml")
PYTHON_VERSION = "3.12.7"
SERVICE_NAME = "saas-demo-app"  # must match Render service name

# Render API
API_BASE = "https://api.render.com/v1"
RENDER_TOKEN = os.getenv("RENDER_API_KEY")  # must be set in env

print("🚀 Render Python Pin Finalizer v3 starting...\n")

# === Step 1: Create or update render.yaml ===
render_yaml_content = f"""services:
  - type: web
    name: saas-demo
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port 10000
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: saas_demo_db
          property: connectionString
      - key: PYTHON_VERSION
        value: "{PYTHON_VERSION}"
"""

RENDER_YAML.write_text(render_yaml_content.strip() + "\n")
print(f"✅ Created clean render.yaml → {RENDER_YAML}")

# === Step 2: Add .python-version ===
(Path(PROJECT_DIR) / ".python-version").write_text(PYTHON_VERSION)
print("✅ Added .python-version")

# === Step 3: Git commit and push changes ===
subprocess.run(["git", "add", "-A"], cwd=PROJECT_DIR)
subprocess.run(["git", "commit", "-m", f"Trigger redeploy: enforce Python {PYTHON_VERSION}"], cwd=PROJECT_DIR)
subprocess.run(["git", "push"], cwd=PROJECT_DIR)
print("✅ Changes pushed — Render will redeploy automatically (no API call needed).")

# === Step 4: (Optional) Wait and check Render deploy ===
if not RENDER_TOKEN:
    print("\n⚠️ No RENDER_API_KEY found. Skipping deploy status check.")
    exit(0)

headers = {"Authorization": f"Bearer {RENDER_TOKEN}"}

# Fetch Render service info
print("\n🔍 Fetching Render service info...")
service_resp = requests.get(f"{API_BASE}/services?name={SERVICE_NAME}", headers=headers)
services = service_resp.json()

if not services or (isinstance(services, dict) and "error" in services):
    print(f"❌ Could not find service '{SERVICE_NAME}'. Response: {services}")
    exit(1)

service_id = None
if isinstance(services, list) and services:
    service_id = services[0].get("id")
elif isinstance(services, dict):
    service_id = services.get("id")

if not service_id:
    print(f"❌ Could not extract service ID from Render response: {services}")
    exit(1)

print(f"✅ Found service '{SERVICE_NAME}' (id={service_id})")

# Wait a bit for Render to begin redeploy
print("⏳ Waiting 30s for Render to start new deploy...")
time.sleep(30)

# Fetch latest deploy info
deploy_url = f"{API_BASE}/services/{service_id}/deploys"
deploy_resp = requests.get(deploy_url, headers=headers)
deploy_data = deploy_resp.json()

latest = None
deploy_id = None

if isinstance(deploy_data, list) and deploy_data:
    latest = deploy_data[0]
    deploy_id = latest.get("id")
    if deploy_id:
        print(f"✅ Latest deploy found: {deploy_id}")
    else:
        print("⚠️ No deploy ID found in latest deploy object.")
else:
    print(f"⚠️ No deploys returned for service {SERVICE_NAME}. Full response: {deploy_data}")

# === Step 5: Poll deploy status if available ===
if deploy_id:
    for _ in range(15):  # check for up to ~2.5 minutes
        time.sleep(10)
        status_resp = requests.get(f"{API_BASE}/deploys/{deploy_id}", headers=headers)
        status_json = status_resp.json()
        status = status_json.get("status")

        if status:
            print(f"   → Current deploy status: {status}")
        else:
            print("⚠️ Could not fetch deploy status.")
            break

        if status in ("live", "succeeded"):
            print("✅ Deploy succeeded!")
            break
        elif status in ("failed", "canceled"):
            print("❌ Deploy failed or canceled.")
            break
    else:
        print("⚠️ Timed out waiting for deploy to complete.")
else:
    print("ℹ️ Skipped deploy polling (no deploy ID available).")

print("\n🎯 Done — Render Python Pin Finalizer v3 complete.")
