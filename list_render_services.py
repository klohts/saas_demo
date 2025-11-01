import os, requests
from dotenv import load_dotenv

load_dotenv(dotenv_path="/home/hp/AIAutomationProjects/saas_demo/.env")

token = os.getenv("RENDER_API_KEY")
if not token:
    print("❌ Missing API key")
    exit(1)

resp = requests.get("https://api.render.com/v1/services", headers={"Authorization": f"Bearer {token}"})
for svc in resp.json():
    print(f"🟢 Service name: {svc.get('name')}, ID: {svc.get('id')}")
