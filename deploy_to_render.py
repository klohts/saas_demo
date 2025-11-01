#!/usr/bin/env python3
"""
Render Auto-Deploy Script — Resilient v2
Author: Ken’s AI Deployment Pipeline (GPT-5)
Date: 2025-11-01
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
    """Run shell command with live output."""
    print(f"\n➡️ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr and (allow_fail or result.returncode != 0):
        print(result.stderr.strip())
    return result

def slack_notify(msg: str):
    """Send Slack notification if webhook configured."""
    if not SLACK_WEBHOOK:
        return
    try:
        requests.post(SLACK_WEBHOOK, json={"text": msg}, timeout=5)
    except Exception:
        print("⚠️ Slack notification failed")

def get_latest_deploy(headers):
    """Return the most recent deploy (ID + timestamp)."""
    resp = requests.get(
        f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/deploys",
        headers=headers,
    )
    if resp.status_code != 200:
        return None, None
    data = resp.json()
    if isinstance(data, list) and len(data) > 0:
        return data[0].get("id"), data[0].get("createdAt")
    return None, None

def trigger_render_deploy():
    """Trigger a new deploy and handle 202 empty responses."""
    print("🚀 Triggering Render redeploy...")
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {RENDER_API_KEY}",
    }

    before_id, before_time = get_latest_deploy(headers)

    resp = requests.post(
        f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/deploys",
        headers=headers,
    )

    # 201 — immediate deploy ID returned
    if resp.status_code == 201:
        data = resp.json()
        deploy_id = data.get("id")
        print(f"✅ Deploy triggered successfully! ID: {deploy_id}")
        return deploy_id

    # 202 — accepted but no deploy ID yet
    if resp.status_code == 202:
        print("⚠️ Render API returned 202 (accepted, deploy not yet visible). Polling for new deploy...")
        for attempt in range(12):  # 12 * 10s = 2 minutes max wait
            time.sleep(10)
            latest_id, latest_time = get_latest_deploy(headers)
            if latest_id and latest_id != before_id:
                print(f"✅ Found new deploy ID after {10*(attempt+1)}s: {latest_id}")
                return latest_id
            print(f"⏳ Still waiting for deploy to appear... ({attempt+1}/12)")
        print("❌ Gave up waiting for new deploy ID after 2 minutes.")
        return None

    print(f"❌ Render deploy failed: {resp.status_code} - {resp.text}")
    return None

def monitor_deploy(deploy_id):
    """Poll Render API until deploy finishes."""
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
            return True
        elif status in ("failed", "canceled"):
            print(f"❌ Deployment failed ({status}). Check Render logs.")
            slack_notify(f"❌ Render Deploy Failed: {status}")
            return False

        time.sleep(10)

def main():
    print("\n🧩 Starting SaaS Auto-Deploy Process...\n")

    run_cmd("git remote -v")
    run_cmd("git add .")

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_cmd(f'git commit -m "Auto-deploy: {ts}" || echo \"No new changes to commit.\"', allow_fail=True)
    run_cmd("git push origin main")

    deploy_id = trigger_render_deploy()
    if not deploy_id:
        print("⚠️ No deploy ID found. Please check Render dashboard manually.")
        sys.exit(1)

    success = monitor_deploy(deploy_id)
    if success:
        print("\n🎯 Done! Your SaaS app is live and up-to-date.\n")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
