import os, requests, time, subprocess, json

SERVICE_NAME = "saas-demo-app"
PYTHON_VERSION = "3.12.7"
API_BASE = "https://api.render.com/v1"
RENDER_API_KEY = os.getenv("RENDER_API_KEY")

headers = {"Authorization": f"Bearer {RENDER_API_KEY}"}

print("🔍 Checking render.yaml...")
yaml_path = "render.yaml"
if not os.path.exists(yaml_path):
    print("⚠️ render.yaml not found. Creating it.")
    with open(yaml_path, "w") as f:
        f.write(f"""services:
  - type: web
    name: {SERVICE_NAME}
    env: python
    pythonVersion: {PYTHON_VERSION}
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn saas_demo.app.main:app --host 0.0.0.0 --port $PORT
""")

else:
    # Ensure correct python version
    with open(yaml_path) as f:
        lines = f.readlines()
    with open(yaml_path, "w") as f:
        for line in lines:
            if "pythonVersion:" in line:
                f.write(f"    pythonVersion: {PYTHON_VERSION}\n")
            else:
                f.write(line)

subprocess.run(["git", "add", yaml_path])
subprocess.run(["git", "commit", "-m", "Fix: enforce Python 3.12.7"], check=False)
subprocess.run(["git", "push"], check=False)

print("✅ render.yaml updated and pushed to GitHub.\n")

print("🔍 Fetching Render services...")
resp = requests.get(f"{API_BASE}/services", headers=headers)
services = resp.json()
service = next((s for s in services if (s.get('name') or s.get('service', {}).get('name')) == SERVICE_NAME), None)

if not service:
    raise SystemExit(f"❌ Service '{SERVICE_NAME}' not found on Render.")
service_id = service.get("id") or service.get("service", {}).get("id")
print(f"✅ Found service '{SERVICE_NAME}' (id={service_id})\n")

print("🚀 Triggering redeploy...")
redeploy = requests.post(f"{API_BASE}/services/{service_id}/deploys", headers=headers)
if redeploy.status_code != 201:
    raise SystemExit(f"❌ Redeploy failed: {redeploy.text}")
deploy_id = redeploy.json()["id"]
print(f"✅ Redeploy triggered (Deploy ID: {deploy_id})\n")

print("⏳ Waiting for deployment to become healthy...")
for i in range(30):
    time.sleep(10)
    status = requests.get(f"{API_BASE}/deploys/{deploy_id}", headers=headers).json()
    phase = status.get("status")
    print(f"   → Status: {phase}")
    if phase == "live":
        print("✅ Deployment is live!\n")
        break
else:
    raise SystemExit("❌ Deployment did not reach live state in time.")

print("🔍 Checking API endpoints...\n")
BASE_URL = "https://ai-email-bot-0xut.onrender.com"
for endpoint in ["/health", "/clients/", "/run-bot"]:
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", timeout=15)
        print(f"{endpoint}: {r.status_code} → {r.text[:200]}")
    except Exception as e:
        print(f"{endpoint}: ❌ {e}")

print("\n🎯 All done! Render Finalizer completed successfully.")
