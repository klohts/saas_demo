import os, time, subprocess, requests
from pathlib import Path

# === CONFIG ===
SERVICE_NAME = "saas-demo-app"
PYTHON_VERSION = "3.12.7"
REPO_ROOT = Path.home() / "AIAutomationProjects"
API_BASE = "https://api.render.com/v1"
RENDER_API_KEY = os.getenv("RENDER_API_KEY")

if not RENDER_API_KEY:
    raise SystemExit("❌ Missing RENDER_API_KEY. Run:\nexport RENDER_API_KEY='your_api_key_here'")

HEADERS = {"Authorization": f"Bearer {RENDER_API_KEY}"}

print("🚀 Render Python Pin Finalizer v2 starting...")

# === STEP 1: Recreate render.yaml at repo root ===
render_yaml = f"""services:
  - type: web
    name: {SERVICE_NAME}
    env: python
    plan: free
    rootDir: .
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn saas_demo.app.main:app --host 0.0.0.0 --port $PORT
    pythonVersion: {PYTHON_VERSION}
"""
render_path = REPO_ROOT / "render.yaml"
render_path.write_text(render_yaml)
print(f"✅ Created clean render.yaml → {render_path}")

# === STEP 2: Add .python-version ===
(REPO_ROOT / ".python-version").write_text(PYTHON_VERSION)
print("✅ Added .python-version")

# === STEP 3: Commit + push ===
subprocess.run(["git", "add", "-f", str(render_path), str(REPO_ROOT / ".python-version")], cwd=REPO_ROOT)
subprocess.run(["git", "commit", "-m", f"Fix: enforce Python {PYTHON_VERSION} + rootDir '.'"], cwd=REPO_ROOT)
subprocess.run(["git", "push"], cwd=REPO_ROOT)
print("✅ Changes committed and pushed to GitHub.")

# === STEP 4: Get service ID ===
print("🔍 Fetching Render service ID...")
resp = requests.get(f"{API_BASE}/services", headers=HEADERS)
if resp.status_code != 200:
    raise SystemExit(f"❌ Could not fetch services: {resp.text}")
services = resp.json()
service = next((s for s in services if s.get("service", {}).get("name") == SERVICE_NAME or s.get("name") == SERVICE_NAME), None)
if not service:
    raise SystemExit(f"❌ Service '{SERVICE_NAME}' not found.")
service_id = service.get("id") or service.get("service", {}).get("id")
print(f"✅ Found service '{SERVICE_NAME}' (id={service_id})")

# === STEP 5: Clear cache ===
print("🧹 Clearing Render build cache...")
clear_url = f"{API_BASE}/services/{service_id}/clear_cache"
r = requests.post(clear_url, headers=HEADERS)
if r.status_code == 200:
    print("✅ Build cache cleared successfully.")
else:
    print(f"⚠️ Cache clear may not be supported on your account: {r.text}")

# === STEP 6: Trigger redeploy ===
print("🚀 Triggering redeploy...")
deploy_url = f"{API_BASE}/services/{service_id}/deploys"
r = requests.post(deploy_url, headers=HEADERS)
if r.status_code != 201:
    raise SystemExit(f"❌ Failed to trigger deploy: {r.text}")
deploy_id = r.json()["id"]
print(f"✅ Redeploy triggered (Deploy ID: {deploy_id})")

# === STEP 7: Wait for logs and verify Python version ===
print("⏳ Waiting for deployment logs (20s)...")
time.sleep(20)
log_url = f"{API_BASE}/deploys/{deploy_id}/logs"
r = requests.get(log_url, headers=HEADERS)

if r.status_code == 200:
    logs = r.text
    if PYTHON_VERSION in logs:
        print(f"🎯 Success! Render is now using Python {PYTHON_VERSION}.")
    elif "3.13" in logs:
        print("⚠️ Still using 3.13 — try manually clearing build cache in Render dashboard.")
    else:
        print("ℹ️ Logs fetched, but version not yet detected — check Render dashboard logs.")
else:
    print(f"⚠️ Could not fetch logs: {r.text}")

print("✅ Done — Python version pin finalized.")
