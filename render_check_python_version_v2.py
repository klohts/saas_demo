import os, requests, re

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
    data = r.json()
    # Handle possible list variations
    deploys = data.get("serviceDeploys") if isinstance(data, dict) else data
    if not deploys:
        print("⚠️ No deploys found for this service.")
        return None

    deploy_id = deploys[0].get("id") or deploys[0].get("deploy", {}).get("id")
    if not deploy_id:
        print("⚠️ Could not find deploy ID in response.")
        return None

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
            print("   Fix: ensure render.yaml is at repo root and pushed with:")
            print("   git add -f render.yaml && git commit -m 'Pin Python 3.12.7' && git push")

    except requests.RequestException as e:
        print("❌ Error communicating with Render API:", e)

if __name__ == "__main__":
    main()
