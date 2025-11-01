import os
import re
import time
import json
import subprocess
import requests

API_BASE = "https://api.render.com/v1"
SERVICE_NAME = "saas-demo-app"
TARGET_PYTHON = "3.12.7"
HEADERS = {"Authorization": f"Bearer {os.getenv('RENDER_API_KEY')}"}

# -----------------------------------------------------
# 1️⃣ Validate and repair render.yaml
# -----------------------------------------------------
def ensure_render_yaml():
    path = os.path.expanduser("~/AIAutomationProjects/render.yaml")
    content = f"""services:
  - type: web
    name: {SERVICE_NAME}
    env: python
    pythonVersion: {TARGET_PYTHON}
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn saas_demo.app.main:app --host 0.0.0.0 --port $PORT
"""
    with open(path, "w") as f:
        f.write(content)
    subprocess.run(["git", "add", "-f", path])
    subprocess.run(["git", "commit", "-m", f"Repair: enforce Python {TARGET_PYTHON} + root render.yaml"], check=False)
    subprocess.run(["git", "push"], check=False)
    print(f"✅ render.yaml fixed and pushed to GitHub root ({path})")
    return path

# -----------------------------------------------------
# 2️⃣ Detect service and fix Root Directory
# -----------------------------------------------------
def get_service_id():
    r = requests.get(f"{API_BASE}/services", headers=HEADERS)
    r.raise_for_status()
    for s in r.json():
        name = s.get("name") or s.get("service", {}).get("name")
        if name == SERVICE_NAME:
            sid = s.get("id") or s.get("service", {}).get("id")
            print(f"✅ Found Render service '{SERVICE_NAME}' (id={sid})")
            return sid
    print(f"❌ Service '{SERVICE_NAME}' not found")
    return None

def fix_root_directory(service_id):
    """Force Root Directory to '/' in Render API."""
    patch_data = {"rootDir": "/"}
    r = requests.patch(f"{API_BASE}/services/{service_id}", headers=HEADERS, json=patch_data)
    if r.status_code in (200, 201):
        print("✅ Root Directory set to '/' on Render.")
    else:
        print(f"⚠️ Could not update Root Directory (status={r.status_code}): {r.text}")

# -----------------------------------------------------
# 3️⃣ Trigger redeploy + verify logs
# -----------------------------------------------------
def trigger_redeploy(service_id):
    r = requests.post(f"{API_BASE}/services/{service_id}/deploys", headers=HEADERS)
    r.raise_for_status()
    deploy_id = r.json().get("id") or r.json().get("deploy", {}).get("id")
    print(f"🚀 Redeploy triggered (Deploy ID: {deploy_id})")
    return deploy_id

def get_logs(deploy_id):
    r = requests.get(f"{API_BASE}/deploys/{deploy_id}/logs", headers=HEADERS)
    if r.status_code == 404:
        return ""
    r.raise_for_status()
    return r.text

def confirm_python_version(deploy_id):
    """Poll logs until 3.12.x appears."""
    print("⏳ Waiting for correct Python version...")
    for _ in range(30):  # ~15 minutes max
        logs = get_logs(deploy_id)
        match = re.search(r"Using Python version\s+([\d\.]+)", logs)
        if match:
            version = match.group(1)
            print(f"🔎 Detected Python {version}")
            if version.startswith("3.12"):
                print("✅ Correct version confirmed!")
                return True
        time.sleep(30)
    print("❌ Timeout — could not confirm Python version.")
    return False

# -----------------------------------------------------
# 🧠 Main
# -----------------------------------------------------
def main():
    print("🧩 Render Nuke + Repair starting...")
    if not os.getenv("RENDER_API_KEY"):
        print("❌ Missing RENDER_API_KEY")
        return

    ensure_render_yaml()
    sid = get_service_id()
    if not sid:
        return

    fix_root_directory(sid)
    dep_id = trigger_redeploy(sid)
    confirm_python_version(dep_id)
    print("\n🎯 Done. Your Render should now use Python 3.12.7 correctly.")

if __name__ == "__main__":
    main()
