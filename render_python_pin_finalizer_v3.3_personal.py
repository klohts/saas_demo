#!/usr/bin/env python3
"""
Render Python Pin Finalizer v3.3 — Personal Workspace Edition
-------------------------------------------------------------
✅ Works perfectly on Hobby/Personal Render accounts (no Team/Workspace key needed)
✅ Uses your manually provided SERVICE_ID (no auto-discovery)
✅ Deploys, monitors status, and logs progress cleanly
"""

import os
import time
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv(dotenv_path="/home/hp/AIAutomationProjects/saas_demo/.env")

# === CONFIGURATION ===
PROJECT_DIR = Path("/home/hp/AIAutomationProjects/saas_demo")
RENDER_YAML = Path("/home/hp/AIAutomationProjects/render.yaml")
PYTHON_VERSION = "3.12.7"
API_BASE = "https://api.render.com/v1"

RENDER_TOKEN = os.getenv("RENDER_API_KEY")
SERVICE_ID = os.getenv("RENDER_SERVICE_ID")  # required for Hobby accounts

print("🚀 Render Python Pin Finalizer v3.3 (Personal Edition) starting...\n")

# === Step 1: Validation ===
if not RENDER_TOKEN:
    print("❌ Missing RENDER_API_KEY. Add it to your .env file.")
    exit(1)

if not SERVICE_ID:
    print("❌ Missing RENDER_SERVICE_ID in .env. Please add your service ID from Render dashboard.")
    print("   Example line in .env:")
    print("   RENDER_SERVICE_ID=srv-d3n2b42li9vc738n9bng")
    exit(1)

# === Step 2: Update render.yaml ===
render_yaml_content = f"""services:
  - type: web
    name: saas-demo
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port 10000
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: saas-demo-db
          property: connectionString
      - key: PYTHON_VERSION
        value: "{PYTHON_VERSION}"
"""
RENDER_YAML.write_text(render_yaml_content.strip() + "\n")
print(f"✅ Updated render.yaml → {RENDER_YAML}")

# === Step 3: Write .python-version ===
(Path(PROJECT_DIR) / ".python-version").write_text(PYTHON_VERSION)
print("✅ Added .python-version")

# === Step 4: Commit + Push ===
subprocess.run(["git", "add", "-A"], cwd=PROJECT_DIR)
commit_msg = f"Trigger redeploy: enforce Python {PYTHON_VERSION}"
subprocess.run(["git", "commit", "-m", commit_msg], cwd=PROJECT_DIR)
subprocess.run(["git", "push"], cwd=PROJECT_DIR)
print("✅ Changes pushed — Render will auto-redeploy.\n")

# === Step 5: Wait and check deploy ===
print(f"🔍 Monitoring service: {SERVICE_ID}")
headers = {"Authorization": f"Bearer {RENDER_TOKEN}"}
deploy_url = f"{API_BASE}/services/{SERVICE_ID}/deploys"

time.sleep(25)  # give Render a moment to register new deploy

try:
    deploys_resp = requests.get(deploy_url, headers=headers)
    deploys = deploys_resp.json()
except Exception as e:
    print(f"⚠️ Could not fetch deploy list: {e}")
    exit(1)

if not isinstance(deploys, list) or not deploys:
    print(f"⚠️ No deploys found for service {SERVICE_ID}. Response: {deploys}")
    exit(0)

deploy_id = deploys[0].get("id")
print(f"✅ Latest deploy ID: {deploy_id}\n")

# === Step 6: Poll for status ===
for i in range(20):  # check for ~3 mins
    time.sleep(10)
    try:
        d = requests.get(f"{API_BASE}/deploys/{deploy_id}", headers=headers).json()
        status = d.get("status")
    except Exception as e:
        print(f"⚠️ Error fetching deploy status: {e}")
        continue

    print(f"   → [{i+1}] Deploy status: {status}")

    if status in ("live", "succeeded"):
        print("✅ Deploy succeeded and is live!")
        break
    elif status in ("failed", "canceled"):
        print("❌ Deploy failed or canceled.")
        break
else:
    print("⚠️ Timed out waiting for deploy to complete.")

print("\n🎯 Done — Render Python Pin Finalizer v3.3 (Personal Edition) complete.")
