import os, re, subprocess, requests

SERVICE_NAME = "saas-demo-app"
API_BASE = "https://api.render.com/v1"
HEADERS = {"Authorization": f"Bearer {os.getenv('RENDER_API_KEY')}"}

# ------------------------- HELPERS -----------------------------

def get_service_id():
    """Get the Render service ID by name."""
    r = requests.get(f"{API_BASE}/services", headers=HEADERS)
    r.raise_for_status()
    for s in r.json():
        name = s.get("name") or s.get("service", {}).get("name")
        if name == SERVICE_NAME:
            return s.get("id") or s.get("service", {}).get("id")
    return None

def get_latest_deploy(service_id):
    """Fetch the most recent deploy for the given service."""
    r = requests.get(f"{API_BASE}/services/{service_id}/deploys", headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    deploys = data.get("serviceDeploys") if isinstance(data, dict) else data
    if not deploys:
        print("⚠️ No deploys found for this service.")
        return None
    return deploys[0]

def get_deploy_logs(deploy_id):
    """Get logs for the given deploy ID."""
    url = f"{API_BASE}/deploys/{deploy_id}/logs"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 404:
        print("⚠️ Logs for this deploy may have expired or been archived.")
        return ""
    r.raise_for_status()
    return r.text

def detect_python_version(logs):
    """Extract the Python version from logs."""
    match = re.search(r"Using Python version\s+([\d\.]+)", logs)
    return match.group(1) if match else None

def patch_render_yaml():
    """Ensure render.yaml is pinned to Python 3.12.7 and at the repo root."""
    yaml_path = os.path.expanduser("~/AIAutomationProjects/render.yaml")
    content = f"""services:
  - type: web
    name: {SERVICE_NAME}
    env: python
    pythonVersion: 3.12.7
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn saas_demo.app.main:app --host 0.0.0.0 --port $PORT
"""
    with open(yaml_path, "w") as f:
        f.write(content)

    subprocess.run(["git", "add", "-f", yaml_path])
    subprocess.run(["git", "commit", "-m", "Auto-heal: enforce Python 3.12.7 on Render"], check=False)
    subprocess.run(["git", "push"], check=False)
    print("✅ render.yaml patched, committed, and pushed to GitHub root.")
    return yaml_path

def trigger_redeploy(service_id):
    """Trigger a fresh Render deployment."""
    r = requests.post(f"{API_BASE}/services/{service_id}/deploys", headers=HEADERS)
    if r.status_code not in (200, 201):
        print(f"❌ Failed to trigger redeploy: {r.status_code} → {r.text}")
        return None
    deploy_id = r.json().get("id") or r.json().get("deploy", {}).get("id")
    print(f"🚀 Redeploy triggered successfully (Deploy ID: {deploy_id})")
    return deploy_id

# ------------------------- MAIN -----------------------------

def main():
    print("🔍 Checking Render deployment health...")

    if not os.getenv("RENDER_API_KEY"):
        print("❌ Missing environment variable: RENDER_API_KEY")
        return

    try:
        service_id = get_service_id()
        if not service_id:
            print(f"❌ Could not find service '{SERVICE_NAME}'.")
            return

        deploy = get_latest_deploy(service_id)
        if not deploy:
            return

        deploy_id = deploy.get("id") or deploy.get("deploy", {}).get("id")
        status = deploy.get("status") or "unknown"
        print(f"📦 Latest deploy ID: {deploy_id} (status: {status})")

        logs = get_deploy_logs(deploy_id)
        version = detect_python_version(logs or "")

        if not version:
            print("⚠️ No Python version detected in logs.")
            print("   Assuming incorrect version and applying auto-heal.")
            patch_render_yaml()
            trigger_redeploy(service_id)
            return

        if version.startswith("3.12"):
            print(f"✅ Render is using Python {version} — correct version! 🎉")
        else:
            print(f"❌ Render is using Python {version} (should be 3.12.7).")
            print("🩺 Applying auto-heal to enforce Python 3.12.7...")
            patch_render_yaml()
            trigger_redeploy(service_id)

    except requests.RequestException as e:
        print(f"❌ Error communicating with Render API: {e}")

if __name__ == "__main__":
    main()
