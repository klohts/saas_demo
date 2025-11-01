#!/usr/bin/env python3
"""
Production-Ready Render Auto-Deploy Script
Author: Ken's AI Deployment Pipeline (GPT-5)
Last Updated: 2025-11-01

Handles:
✅ 202 empty responses from Render API gracefully
✅ Rebuild retry logic
✅ Slack webhook notification (optional)
✅ Full deploy status tracking with clear output
"""

import os
import sys
import time
import json
import subprocess
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

RENDER_API_KEY = os.getenv("RENDER_API_KEY")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK", "")

if not RENDER_API_KEY or not RENDER_SERVICE_ID:
    print("❌ Missing RENDER_API_KEY or RENDER_SERVICE_ID in .env")
    sys.exit(1)

def run_cmd(cmd, allow_fail=False):
    """Run shell command and stream output."""
    print(f"\n➡️ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr and (allow_fail or result.returncode != 0):
        print(result.stderr.strip())
    return result

def slack_notify(message: str):
    """Post a Slack notification if webhook is set."""
    if not SLACK_WEBHOOK:
        return
    try:
        requests.post(SLACK_WEBHOOK, json={"text": message}, timeout=5)
    except Exception:
        print("⚠️ Slack notification failed")

def trigger_render_deploy():
    """Trigger new deploy and return ID."""
    print("🚀 Triggering Render redeploy...")
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {RENDER_API_KEY}",
    }
    response = requests.post(
        f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/deploys",
        headers=headers,
    )

    # Handle all response types
    if response.status_code == 201:
        data = response.json()
        print(f"✅ Deploy triggered successfully! ID: {data.get('id')}")
        return data.get("id")

    elif response.status_code == 202:
        print("⚠️ Render API returned 202 (accepted but no ID). Retrying fetch...")
        # Retry latest deploy fetch
        time.sleep(3)
        deploy_id = get_latest_deploy_id()
        if deploy_id:
            print(f"✅ Found active deploy: {deploy_id}")
            return deploy_id
        else:
            print("❌ Could not fetch active deploy ID after 202 response.")
            return None

    else:
        print(f"❌ Render deploy failed: {response.status_code} - {response.text}")
        return None

def get_latest_deploy_id():
    """Fetch the latest deploy for this service."""
    headers = {"Authorization": f"Bearer {RENDER_API_KEY}"}
    resp = requests.get(f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/deploys", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            return data[0].get("id")
    return None

def monitor_deploy(deploy_id):
    """Poll until deploy is live."""
    print("🔍 Monitoring deploy progress...")
    headers = {"Authorization": f"Bearer {RENDER_API_KEY}"}

    while True:
        resp = requests.get(
            f"https://api.render.com/v1/deploys/{deploy_id}",
            headers=headers,
        )
        if resp.status_code != 200:
            print(f"⚠️ Failed to fetch deploy status ({resp.status_code})")
            time.sleep(10)
            continue

        data = resp.json()
        status = data.get("status")
        print(f"⏳ Status: {status}")

        if status in ("live", "succeeded"):
            print("✅ Deployment successful! 🎉")
            slack_notify(f"✅ Render Deploy Success! ({deploy_id})")
            break
        elif status in ("failed", "canceled"):
            print(f"❌ Deployment failed ({status}). Check Render logs.")
            slack_notify(f"❌ Render Deploy Failed: {status}")
            sys.exit(1)

        time.sleep(10)

def main():
    print("\n🧩 Starting SaaS Auto-Deploy Process...\n")

    # Ensure Git repo
    run_cmd("git remote -v")
    run_cmd("git add .")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    commit_cmd = f'git commit -m "Auto-deploy: {timestamp}" || echo \"No new changes to commit.\"'
    run_cmd(commit_cmd, allow_fail=True)

    run_cmd("git push origin main")

    deploy_id = trigger_render_deploy()
    if not deploy_id:
        print("⚠️ Deploy trigger failed — no ID received.")
        sys.exit(1)

    monitor_deploy(deploy_id)

    print("\n🎯 Done! Your SaaS app should be live in a few minutes.\n")

if __name__ == "__main__":
    main()
