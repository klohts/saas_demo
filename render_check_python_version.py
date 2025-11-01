import os, requests, re

# Configuration
SERVICE_NAME = "saas-demo-app"
API_BASE = "https://api.render.com/v1"
HEADERS = {"Authorization": f"Bearer {os.getenv('RENDER_API_KEY')}"}

def get_service_id():
    r = requests.get(f"{API_BASE}/services", headers=HEADERS)
    r.raise_for_status()
    for s in r.json():
        name = s.get("name") or s.get("service", {}).get("name")
        if name == SERVICE_NAME:
            return s.get("id") or s.get("service", {}).get("id")
    return None

def get_latest_deploy_logs(service_id):
    r = requests.get(f"{API_BASE}/services/{service_id}/deploys", headers=HEADERS)
    r.raise_for_status()
    deploys = r.json()
    if not deploys:
        return None
    deploy_id = deploys[0]["id"]
    logs_url = f"{API_BASE}/deploys/{deploy_id}/logs"
    r_logs = requests.get(logs_url, headers=HEADERS)
    r_logs.raise_for_status()
    return r_logs.text

def detect_python_version(logs: str):
    match = re.search(r"Using Python version\s+([\d\.]+)", logs)
    return match.group(1) if match else None

def main():
    print("🔍 Checking deployed Python version on Render...")

    key = os.getenv("RENDER_API_KEY")
    if not key:
        print("❌ Missing environment variable: RENDER_API_KEY")
        print("   Run: export RENDER_API_KEY=\"your_key_here\"")
        return

    try:
        service_id = get_service_id()
        if not service_id:
            print(f"❌ Could not find service '{SERVICE_NAME}'.")
            return

        logs = get_latest_deploy_logs(service_id)
        if not logs:
            print("⚠️ Could not fetch deployment logs.")
            return

        version = detect_python_version(logs)
        if not version:
            print("⚠️ No Python version detected in logs.")
            return

        if version.startswith("3.12"):
            print(f"✅ Render is using Python {version} — correct version!")
        else:
            print(f"❌ Render is using Python {version} (should be 3.12.7).")
            print("   Please ensure render.yaml is at the repo root and pushed with:")
            print("   git add -f render.yaml && git commit -m 'Pin Python 3.12.7' && git push")

    except requests.RequestException as e:
        print("❌ Error communicating with Render API:", e)

if __name__ == "__main__":
    main()
