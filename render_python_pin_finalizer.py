import os
import requests
import subprocess
import time
from pathlib import Path

# === CONFIG ===
SERVICE_ID = "srv-d3n2b42li9vc738n9bng"  # Your Render service ID
PYTHON_VERSION = "3.12.7"
REPO_ROOT = Path.home() / "AIAutomationProjects"
RENDER_API_KEY = os.getenv("RENDER_API_KEY")
API_BASE = "https://api.render.com/v1"

# === CHECKS ===
if not RENDER_API_KEY:
    raise SystemExit("❌ Missing RENDER_API_KEY. Run:\nexport RENDER_API_KEY='your_api_key_here'")

print("🚀 Render Python Pin Finalizer starting...")

# === STEP 1: Create clean render.yaml ===
render_yaml = f"""services:
  - type: web
    name: saas-demo-app
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn saas_demo.app.main:app --host 0.0.0.0 --port $PORT
    pythonVersion: {PYTHON_VERSION}
"""

render_path = REPO_ROOT / "render.yaml"
render_path.write_text(render_yaml)
print(f"✅ Created clean render.yaml → {render_path}")

# === STEP 2: Add .python-version ===
python_version_path = REPO_ROOT / ".python-version"
python_version_path.write_text(PYTHON_VERSION)
print(f"✅ Added .python-version → {python_version_path}")

# === STEP 3: Commit and push to GitHub ===
subprocess.run(["git", "add", "-f", str(render_path), str(python_version_path)], cwd=REPO_ROOT)
subprocess.run(["git", "commit", "-m", f"Fix: enforce Python {PYTHON_VERSION} + clean render.yaml"], cwd=REPO_ROOT)
subprocess.run(["git", "push"], cwd=REPO_ROOT)
print("✅ Changes committed and pushed to GitHub.")

# === STEP 4: Clear build cache ===
print("🧹 Clearing Render build cache...")
clear_cache_url = f"{API_BASE}/services/{SERVICE_ID}/clear-cache"
r = requests.post(clear_cache_url, headers={"Authorization": f"Bearer {RENDER_API_KEY}"})
if r.status_code == 200:
    print("✅ Build cache cleared successfully.")
else:
    print(f"⚠️ Failed to clear cache: {r.text}")

# === STEP 5: Trigger redeploy ===
print("🚀 Triggering redeploy...")
deploy_url = f"{API_BASE}/services/{SERVICE_ID}/deploys"
r = requests.post(deploy_url, headers={"Authorization": f"Bearer {RENDER_API_KEY}"})
if r.status_code != 201:
    raise SystemExit(f"❌ Failed to trigger deploy: {r.text}")
deploy_id = r.json()["id"]
print(f"✅ Redeploy triggered (Deploy ID: {deploy_id})")

# === STEP 6: Wait for deploy logs and verify Python version ===
print("⏳ Waiting for deployment logs (this may take ~20s)...")
time.sleep(20)

logs_url = f"{API_BASE}/deploys/{deploy_id}/logs"
r = requests.get(logs_url, headers={"Authorization": f"Bearer {RENDER_API_KEY}"})
if r.status_code == 200:
    logs = r.text
    if PYTHON_VERSION in logs:
        print(f"🎯 Verified! Render is using Python {PYTHON_VERSION}.")
    elif "3.13" in logs:
        print("⚠️ Still using Python 3.13 — something is cached in Render. Try manual cache clear in dashboard.")
    else:
        print("ℹ️ Logs fetched but version string not found yet. Check Render dashboard logs for confirmation.")
else:
    print(f"⚠️ Failed to fetch logs: {r.text}")

print("✅ Done! Render Python version enforcement completed.")
