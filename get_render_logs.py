#!/usr/bin/env python3
"""
get_render_logs.py
------------------
Fetch and print logs for the latest Render deploy
Works perfectly with Personal / Hobby Render API keys.

Usage:
  python get_render_logs.py
"""

import os
import requests
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv(dotenv_path="/home/hp/AIAutomationProjects/saas_demo/.env")

API_BASE = "https://api.render.com/v1"
RENDER_TOKEN = os.getenv("RENDER_API_KEY")
SERVICE_ID = os.getenv("RENDER_SERVICE_ID")

if not RENDER_TOKEN:
    print("❌ Missing RENDER_API_KEY in .env")
    exit(1)
if not SERVICE_ID:
    print("❌ Missing RENDER_SERVICE_ID in .env")
    exit(1)

headers = {"Authorization": f"Bearer {RENDER_TOKEN}"}

print(f"🔍 Fetching latest deploy logs for service: {SERVICE_ID}\n")

# === Step 1: Get latest deploy ID ===
deploy_url = f"{API_BASE}/services/{SERVICE_ID}/deploys"
r = requests.get(deploy_url, headers=headers)
if r.status_code != 200:
    print(f"❌ Failed to fetch deploys: {r.status_code} {r.text[:200]}")
    exit(1)

try:
    deploys = r.json()
except Exception as e:
    print(f"❌ JSON parse error: {e}")
    print(r.text[:300])
    exit(1)

if not isinstance(deploys, list) or not deploys:
    print(f"⚠️ No deploys found for service {SERVICE_ID}.")
    exit(0)

latest = deploys[0]
deploy_id = latest.get("deploy", {}).get("id") or latest.get("id")
status = latest.get("deploy", {}).get("status") or latest.get("status")
commit_msg = latest.get("deploy", {}).get("commit", {}).get("message")

print(f"✅ Latest deploy: {deploy_id} (status: {status})")
if commit_msg:
    print(f"   Commit: {commit_msg}")

# === Step 2: Fetch logs ===
logs_url = f"{API_BASE}/deploys/{deploy_id}/logs"
r_logs = requests.get(logs_url, headers=headers)

if r_logs.status_code != 200:
    print(f"❌ Could not fetch logs (HTTP {r_logs.status_code})")
    print(r_logs.text[:200])
    exit(1)

try:
    logs_data = r_logs.json()
except Exception as e:
    print(f"⚠️ Non-JSON log output — printing raw:")
    print(r_logs.text[:500])
    exit(0)

# === Step 3: Display logs ===
print("\n�� --- Render Deploy Logs ---\n")

logs = logs_data.get("logs") or logs_data
if isinstance(logs, list):
    for entry in logs[-100:]:  # last 100 lines
        print(entry.get("message") or str(entry))
else:
    print(str(logs)[:2000])

print("\n✅ End of logs.\n")
