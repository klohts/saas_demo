#!/usr/bin/env python3
"""
Render Python Pin Finalizer v3.1 — Hardened & Dotenv-Ready
-----------------------------------------------------------
Automates Render YAML cleanup, pins Python version, commits and pushes changes,
and confirms redeploy status using the Render API safely.

Enhancements in v3.1:
- Loads API key from .env automatically
- Uses correct Render API endpoint (/v1/services)
- Handles empty or invalid JSON gracefully
- Provides detailed debug logs for every stage
"""

import os
import time
import json
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()

# === CONFIGURATION ===
PROJECT_DIR = Path("/home/hp/AIAutomationProjects/saas_demo")
RENDER_YAML = Path("/home/hp/AIAutomationProjects/render.yaml")
PYTHON_VERSION = "3.12.7"
SERVICE_NAME = "saas-demo-app"  # must match Render service name exactly
API_BASE = "https://api.render.com/v1"

RENDER_TOKEN = os.getenv("RENDER_API_KEY")

print("🚀 Render Python Pin Finalizer v3.1 starting...\n")

# === Step 1: Validate configuration ===
if not RENDER_TOKEN:
    print("❌ Missing Render API key. Please set RENDER_API_KEY in .env or environment.")
    exit(1)

# === Step 2: Create or update render.yaml ===
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

# === Step 3: Add .python-version ===
(Path(PROJECT_DIR) / ".python-version").write_text(PYTHON_VERSION)
print("✅ Added .python-version")

# === Step 4: Commit and push changes ===
subprocess.run(["git", "add", "-A"], cwd=PROJECT_DIR)
commit_msg = f"Trigger redeploy: enforce Python {PYTHON_VERSION}"
subprocess.run(["git", "commit", "-m", commit_msg], cwd=PROJECT_DIR)
subprocess.run(["git", "push"], cwd=PROJECT_DIR)
print("✅ Changes pushed — Render will redeploy automatically (no API call needed).")

# === Step 5: Fetch Render service info ===
headers = {"Authorization": f"Bearer {RENDER_TOKEN}"}
print(f"\n🔍 Fetching Render service info for '{SERVICE_NAME}'...")

service_resp = requests.get(f"{API_BASE}/services", headers=headers)
if service_resp.status_code != 200:
    print(f"❌ Render API returned HTTP {service_resp.status_code}: {service_resp.text[:300]}")
    exit(1)

try:
    services = service_resp.json()
except requests.exceptions.JSONDecodeError:
    print(f"❌ Could not decode JSON. Raw response:\n{service_resp.text[:300]}")
    exit(1)

if not isinstance(services, list):
    print(f"⚠️ Unexpected response format: {services}")
    exit(1)

service_id = None
for svc in services:
    if svc.get("name") == SERVICE_NAME:
        service_id = svc.get("id")
        break

if not service_id:
    print(f"❌ Could not find service '{SERVICE_NAME}'. Available services: {[s.get('name') for s in services]}")
    exit(1)

print(f"✅ Found service '{SERVICE_NAME}' (id={service_id})")

# === Step 6: Wait for redeploy ===
print("⏳ Waiting 30s for Render to start new deploy...")
time.sleep(30)

deploy_url = f"{API_BASE}/services/{service_id}/deploys"
deploy_resp = requests.get(deploy_url, headers=headers)

if deploy_resp.status_code != 200:
    print(f"❌ Failed to fetch deploys (HTTP {deploy_resp.status_code}): {deploy_resp.text[:200]}")
    exit(1)

try:
    deploy_data = deploy_resp.json()
except requests.exceptions.JSONDecodeError:
    print(f"❌ Could not parse deploy JSON: {deploy_resp.text[:200]}")
    exit(1)

deploy_id = None
if isinstance(deploy_data, list) and deploy_data:
    deploy_id = deploy_data[0].get("id")
    print(f"✅ Latest deploy found: {deploy_id}")
else:
    print(f"⚠️ No deploys found for '{SERVICE_NAME}'. Full response: {deploy_data}")

# === Step 7: Poll deploy status ===
if deploy_id:
    print("🔁 Monitoring deploy progress...")
    for i in range(15):  # ~2.5 minutes total
        time.sleep(10)
        status_resp = requests.get(f"{API_BASE}/deploys/{deploy_id}", headers=headers)
        try:
            status_data = status_resp.json()
        except requests.exceptions.JSONDecodeError:
            print("⚠️ JSON decode error in deploy status response.")
            continue

        status = status_data.get("status")
        if not status:
            print("⚠️ Missing deploy status key.")
            continue

        print(f"   → Deploy status: {status}")

        if status in ("live", "succeeded"):
            print("✅ Deploy succeeded and is live!")
            break
        elif status in ("failed", "canceled"):
            print("❌ Deploy failed or canceled.")
            break
    else:
        print("⚠️ Timed out waiting for deploy to complete.")
else:
    print("ℹ️ Skipped deploy monitoring — no deploy ID available.")

print("\n🎯 Done — Render Python Pin Finalizer v3.1 complete.")
