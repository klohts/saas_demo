#!/usr/bin/env python3
import os, subprocess, sys, requests, time
from dotenv import load_dotenv

load_dotenv()

REPO_PATH = os.getcwd()
SERVICE_ID = os.getenv("RENDER_SERVICE_ID")
RENDER_API_KEY = os.getenv("RENDER_API_KEY")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")

def slack_notify(message: str):
    if SLACK_WEBHOOK:
        try:
            requests.post(SLACK_WEBHOOK, json={"text": f"🟢 {message}"})
        except Exception:
            print("⚠️ Slack notification failed")

def run_cmd(cmd):
    """Run a shell command safely and stream output."""
    print(f"\n➡️ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error running command:\n{result.stderr}")
        sys.exit(1)
    if result.stdout.strip():
        print(result.stdout.strip())
    return result.stdout.strip()

def ensure_git_repo():
    """Check git setup and remote."""
    if not os.path.exists(".git"):
        print("❌ No git repo found. Run `git init` first.")
        sys.exit(1)

    try:
        remotes = run_cmd("git remote -v")
        if "github.com" not in remotes:
            print("⚠️ No GitHub remote found. Add one using:")
            print("   git remote add origin https://github.com/yourusername/yourrepo.git")
            sys.exit(1)
    except Exception:
        sys.exit("❌ Failed to check git remotes.")

def git_commit_and_push():
    """Auto-commit all changes."""
    run_cmd("git add .")
    msg = f"Auto-deploy: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    run_cmd(f'git commit -m "{msg}" || echo "No new changes to commit."')
    run_cmd("git push origin main")

def trigger_render_deploy():
    """Trigger a deploy using Render API."""
    if not RENDER_API_KEY or not SERVICE_ID:
        print("❌ Missing RENDER_API_KEY or RENDER_SERVICE_ID in .env.")
        sys.exit(1)

    print("🚀 Triggering Render redeploy...")
    headers = {"Authorization": f"Bearer {RENDER_API_KEY}", "Accept": "application/json"}
    url = f"https://api.render.com/v1/services/{SERVICE_ID}/deploys"
    resp = requests.post(url, headers=headers)
    if resp.status_code != 201:
        print(f"❌ Render deploy failed: {resp.status_code} - {resp.text}")
        sys.exit(1)

    deploy_info = resp.json()
    deploy_id = deploy_info.get("id")
    print(f"✅ Deploy triggered successfully! ID: {deploy_id}")
    slack_notify(f"Render redeploy started successfully for service `{SERVICE_ID}`.")
    return deploy_id

def monitor_deploy(deploy_id):
    """Poll Render API for deploy status."""
    print("🔍 Monitoring deploy progress...")
    headers = {"Authorization": f"Bearer {RENDER_API_KEY}"}
    url = f"https://api.render.com/v1/services/{SERVICE_ID}/deploys/{deploy_id}"

    for i in range(20):
        time.sleep(15)
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            print("⚠️ Could not fetch deploy status.")
            continue
        data = resp.json()
        status = data.get("status", "").lower()
        print(f"⏳ Status: {status}")
        if status in ("live", "succeeded"):
            print("✅ Deployment successful! 🎉")
            slack_notify(f"✅ Render deployment succeeded for service `{SERVICE_ID}`.")
            return
        elif status in ("failed", "cancelled", "deactivated"):
            print(f"❌ Deployment failed ({status}). Check logs on Render.")
            slack_notify(f"❌ Render deployment failed ({status}).")
            sys.exit(1)
    print("⚠️ Timed out waiting for deploy to complete.")
    slack_notify("⚠️ Render deploy monitoring timed out.")

def main():
    print("\n🧩 Starting SaaS Auto-Deploy Process...\n")
    ensure_git_repo()
    git_commit_and_push()
    deploy_id = trigger_render_deploy()
    monitor_deploy(deploy_id)
    print("\n🎯 Done! Your SaaS app should be live in a few minutes.")

if __name__ == "__main__":
    main()
