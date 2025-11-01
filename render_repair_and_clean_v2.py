import os
import re
import time
import subprocess
import requests
import socket
from pathlib import Path
from requests.adapters import HTTPAdapter, Retry

# === FORCE IPv4 RESOLUTION ===
import requests.packages.urllib3.util.connection as urllib3_cn
def force_ipv4():
    def allowed_gai_family():
        return socket.AF_INET
    urllib3_cn.allowed_gai_family = allowed_gai_family
force_ipv4()

# === CONFIG ===
API_BASE = "https://api.render.com/v1"
SERVICE_NAME = "saas-demo-app"
TARGET_PYTHON = "3.12.7"
REPO_ROOT = Path.home() / "AIAutomationProjects"
HEADERS = {"Authorization": f"Bearer {os.getenv('RENDER_API_KEY')}"}

# === Setup resilient requests session ===
session = requests.Session()
retries = Retry(total=6, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))

# === 1️⃣ render.yaml ===
def ensure_render_yaml():
    yaml_path = REPO_ROOT / "render.yaml"
    yaml_content = f"""services:
  - type: web
    name: {SERVICE_NAME}
    env: python
    pythonVersion: {TARGET_PYTHON}
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn saas_demo.app.main:app --host 0.0.0.0 --port $PORT
"""
    yaml_path.write_text(yaml_content)
    subprocess.run(["git", "add", "-f", str(yaml_path)], check=False)
    subprocess.run(["git", "commit", "-m", f"Repair: enforce Python {TARGET_PYTHON}"], check=False)
    subprocess.run(["git", "push"], check=False)
    print(f"✅ render.yaml rewritten and pushed to {yaml_path}")
    return yaml_path

# === 2️⃣ GET SERVICE ID ===
def get_service_id():
    r = session.get(f"{API_BASE}/services", headers=HEADERS)
    r.raise_for_status()
    for s in r.json():
        name = s.get("name") or s.get("service", {}).get("name")
        if name == SERVICE_NAME:
            sid = s.get("id") or s.get("service", {}).get("id")
            print(f"✅ Found Render service '{SERVICE_NAME}' (id={sid})")
            return sid
    print("❌ Could not find service in Render account.")
    return None

# === 3️⃣ FIX ROOT DIRECTORY ===
def fix_root_directory(service_id):
    payload = {"rootDir": ""}  # ✅ must be relative, not "/"
    r = session.patch(f"{API_BASE}/services/{service_id}", headers=HEADERS, json=payload)
    if r.status_code in (200, 201):
        print("✅ Root Directory set to repository root ('').")
    else:
        print(f"⚠️ Failed to update Root Directory: {r.text}")

# === 4️⃣ REDEPLOY ===
def trigger_redeploy(service_id):
    r = session.post(f"{API_BASE}/services/{service_id}/deploys", headers=HEADERS)
    r.raise_for_status()
    deploy_id = r.json().get("id") or r.json().get("deploy", {}).get("id")
    print(f"🚀 Redeploy triggered (Deploy ID: {deploy_id})")
    return deploy_id

# === 5️⃣ CHECK PYTHON VERSION ===
def check_python_version(deploy_id):
    print("⏳ Monitoring deployment logs for Python version...")
    for _ in range(30):  # ~15 minutes max
        time.sleep(30)
        r = session.get(f"{API_BASE}/deploys/{deploy_id}/logs", headers=HEADERS)
        if r.status_code != 200:
            continue
        match = re.search(r"Using Python version\s+([\d\.]+)", r.text)
        if match:
            version = match.group(1)
            print(f"🔎 Detected Python {version}")
            if version.startswith("3.12"):
                print("✅ Correct Python version confirmed (3.12.x)")
                return True
    print("❌ Timeout: Python version not confirmed.")
    return False

# === 6️⃣ CLEANUP ===
def cleanup_helper_scripts():
    target_dir = Path("~/AIAutomationProjects/saas_demo").expanduser()
    remove_list = [f for f in target_dir.glob("render_*.py")] + [f for f in target_dir.glob("fix_*.py")]
    deleted = []
    for f in remove_list:
        if f.name != "render_repair_and_clean_v2.py":
            f.unlink()
            deleted.append(f.name)
    if deleted:
        subprocess.run(["git", "add", "-A"], check=False)
        subprocess.run(["git", "commit", "-m", "Cleanup: remove helper scripts"], check=False)
        subprocess.run(["git", "push"], check=False)
        print(f"🧹 Deleted helper scripts: {', '.join(deleted)}")
    else:
        print("✨ No helper scripts to remove — already clean.")

# === MAIN ===
def main():
    print("🩺 Render Repair & Cleanup v2 (IPv4-safe) starting...")
    if not os.getenv("RENDER_API_KEY"):
        print("❌ Missing RENDER_API_KEY.")
        return
    ensure_render_yaml()
    sid = get_service_id()
    if not sid:
        return
    fix_root_directory(sid)
    dep_id = trigger_redeploy(sid)
    ok = check_python_version(dep_id)
    if ok:
        cleanup_helper_scripts()
        print("\n🎯 SUCCESS: Render now uses Python 3.12.7 and repo cleaned.")
    else:
        print("\n⚠️ Repair attempted but Python version not confirmed yet.")

if __name__ == "__main__":
    main()
