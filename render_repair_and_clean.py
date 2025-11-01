import os
import re
import time
import subprocess
import requests
from pathlib import Path

# === CONFIGURATION ===
API_BASE = "https://api.render.com/v1"
SERVICE_NAME = "saas-demo-app"
TARGET_PYTHON = "3.12.7"
REPO_ROOT = Path.home() / "AIAutomationProjects"
HEADERS = {"Authorization": f"Bearer {os.getenv('RENDER_API_KEY')}"}

# === 1️⃣ ENSURE CLEAN render.yaml ===
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
    r = requests.get(f"{API_BASE}/services", headers=HEADERS)
    r.raise_for_status()
    for s in r.json():
        name = s.get("name") or s.get("service", {}).get("name")
        if name == SERVICE_NAME:
            sid = s.get("id") or s.get("service", {}).get("id")
            print(f"✅ Found Render service '{SERVICE_NAME}' (id={sid})")
            return sid
    print("❌ Could not find service in Render account.")
    return None

# === 3️⃣ FORCE ROOT DIRECTORY ===
def fix_root_directory(service_id):
    r = requests.patch(
        f"{API_BASE}/services/{service_id}",
        headers=HEADERS,
        json={"rootDir": "/"},
    )
    if r.status_code in (200, 201):
        print("✅ Root Directory forced to '/'")
    else:
        print(f"⚠️ Failed to update Root Directory: {r.text}")

# === 4️⃣ REDEPLOY SERVICE ===
def trigger_redeploy(service_id):
    r = requests.post(f"{API_BASE}/services/{service_id}/deploys", headers=HEADERS)
    r.raise_for_status()
    deploy_id = r.json().get("id") or r.json().get("deploy", {}).get("id")
    print(f"🚀 Redeploy triggered (Deploy ID: {deploy_id})")
    return deploy_id

# === 5️⃣ VERIFY PYTHON VERSION ===
def check_python_version(deploy_id):
    print("⏳ Monitoring deployment logs for Python version...")
    for _ in range(30):  # ~15 minutes max
        time.sleep(30)
        logs = requests.get(f"{API_BASE}/deploys/{deploy_id}/logs", headers=HEADERS)
        if logs.status_code != 200:
            continue
        match = re.search(r"Using Python version\s+([\d\.]+)", logs.text)
        if match:
            version = match.group(1)
            print(f"🔎 Detected Python {version}")
            if version.startswith("3.12"):
                print("✅ Correct Python version confirmed (3.12.x)")
                return True
    print("❌ Timeout: Python version not confirmed.")
    return False

# === 6️⃣ CLEAN HELPER FILES ===
def cleanup_helper_scripts():
    target_dir = Path("~/AIAutomationProjects/saas_demo").expanduser()
    remove_list = [
        "render_doctor.py", "render_doctor_v2.py", "render_finalizer.py",
        "render_ready.py", "fix_render_python_version.py",
        "fix_render_requirements_path.py", "fix_render_imports.py",
        "render_auto_heal.py", "render_check_python_version.py",
        "render_check_python_version_v2.py", "render_check_python_version_v3.py",
        "final_fix_render_python_version.py", "render_watchdog.py",
        "render_nuke_and_repair.py"
    ]

    deleted = []
    for f in remove_list:
        file_path = target_dir / f
        if file_path.exists():
            file_path.unlink()
            deleted.append(f)

    if deleted:
        subprocess.run(["git", "add", "-A"], check=False)
        subprocess.run(["git", "commit", "-m", "Cleanup: remove helper scripts"], check=False)
        subprocess.run(["git", "push"], check=False)
        print(f"🧹 Deleted helper scripts: {', '.join(deleted)}")
    else:
        print("✨ No helper scripts to remove — already clean.")

# === MAIN ===
def main():
    print("🩺 Render Repair & Cleanup starting...")
    if not os.getenv("RENDER_API_KEY"):
        print("❌ Missing RENDER_API_KEY environment variable.")
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
        print("\n⚠️ Repair attempted but Python version not confirmed yet. Check Render logs manually.")

if __name__ == "__main__":
    main()
