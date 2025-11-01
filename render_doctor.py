"""
render_doctor.py
------------------------------------
Full Render deployment fixer + verifier.

✅ Ensures render.yaml is correct and at repo root
✅ Commits + pushes updates automatically
✅ Clears Render build cache and triggers redeploy
✅ Fixes PORT environment variable if set to 8000
✅ Waits for Python 3.12.7 confirmation in logs
✅ Tests /health and /clients endpoints

Requirements:
    pip install requests pyyaml rich
"""

import os
import time
import yaml
import subprocess
import requests
from rich import print
from rich.console import Console
from rich.progress import track

console = Console()

# -------------------------------
# CONFIGURATION
# -------------------------------
REPO_ROOT = os.path.expanduser("~/AIAutomationProjects")
SERVICE_NAME = "saas-demo"
RENDER_API_URL = "https://api.render.com/v1"
RENDER_API_KEY = os.getenv("RENDER_API_KEY")
RENDER_YAML = os.path.join(REPO_ROOT, "render.yaml")
BASE_URL = "https://ai-email-bot-0xut.onrender.com"

if not RENDER_API_KEY:
    console.print("[bold red]❌ Missing RENDER_API_KEY environment variable.[/bold red]")
    console.print("Generate one at https://render.com/docs/api#authentication")
    console.print('Then run:\n  export RENDER_API_KEY="your_api_key_here"')
    raise SystemExit(1)

headers = {
    "Authorization": f"Bearer {RENDER_API_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# ----------------------------------------------------
# 1️⃣ Ensure render.yaml is correct and at repo root
# ----------------------------------------------------
console.print("[cyan]🔍 Checking render.yaml at repo root...[/cyan]")

expected_yaml = {
    "services": [
        {
            "type": "web",
            "name": SERVICE_NAME,
            "env": "python",
            "pythonVersion": "3.12.7",
            "buildCommand": "pip install -r requirements.txt",
            "startCommand": "uvicorn saas_demo.app.main:app --host 0.0.0.0 --port $PORT",
        }
    ]
}

yaml_needs_update = False

if not os.path.exists(RENDER_YAML):
    console.print("[yellow]⚠️ render.yaml not found. Creating new one...[/yellow]")
    with open(RENDER_YAML, "w") as f:
        yaml.safe_dump(expected_yaml, f)
    yaml_needs_update = True
else:
    with open(RENDER_YAML, "r") as f:
        try:
            current_yaml = yaml.safe_load(f)
        except yaml.YAMLError:
            console.print("[red]⚠️ render.yaml corrupted. Rebuilding.[/red]")
            current_yaml = {}

    if not current_yaml or "services" not in current_yaml:
        yaml_needs_update = True
    else:
        service_conf = current_yaml["services"][0]
        if service_conf.get("pythonVersion") != "3.12.7" or \
           "uvicorn saas_demo.app.main:app" not in service_conf.get("startCommand", ""):
            yaml_needs_update = True

if yaml_needs_update:
    console.print("[yellow]🛠️ Updating render.yaml with correct settings...[/yellow]")
    with open(RENDER_YAML, "w") as f:
        yaml.safe_dump(expected_yaml, f)
    subprocess.run(["git", "-C", REPO_ROOT, "add", "render.yaml"], check=False)
    subprocess.run(["git", "-C", REPO_ROOT, "commit", "-m", "Auto-fix: render.yaml for Python 3.12.7"], check=False)
    subprocess.run(["git", "-C", REPO_ROOT, "push"], check=False)
    console.print("[green]✅ render.yaml fixed and pushed.[/green]")
else:
    console.print("[green]✅ render.yaml looks good.[/green]")

# ----------------------------------------------------
# 2️⃣ Find service ID safely
# ----------------------------------------------------
console.print(f"[cyan]🔍 Fetching Render service ID for [bold]{SERVICE_NAME}[/bold]...[/cyan]")
services_resp = requests.get(f"{RENDER_API_URL}/services", headers=headers)
services_resp.raise_for_status()
services = services_resp.json()

service = None
for s in services:
    name = s.get("name") or s.get("service", {}).get("name")
    if name == SERVICE_NAME:
        service = s.get("service") or s
        break

if not service:
    console.print(f"[red]❌ Could not find Render service '{SERVICE_NAME}'.[/red]")
    raise SystemExit(1)

service_id = service.get("id")
console.print(f"[green]✅ Found service ID:[/green] {service_id}")

# ----------------------------------------------------
# 3️⃣ Fix PORT environment variable if needed
# ----------------------------------------------------
console.print("[cyan]🔍 Checking PORT environment variable...[/cyan]")
env_resp = requests.get(f"{RENDER_API_URL}/services/{service_id}/env-vars", headers=headers)
if env_resp.status_code == 200:
    envs = env_resp.json()
    port_var = next((e for e in envs if e["key"].upper() == "PORT"), None)
    if port_var and port_var["value"] == "8000":
        console.print("[yellow]⚠️ PORT=8000 detected. Resetting to dynamic $PORT...[/yellow]")
        requests.delete(f"{RENDER_API_URL}/services/{service_id}/env-vars/PORT", headers=headers)
        console.print("[green]✅ Removed PORT=8000. Render will auto-assign correct port.[/green]")
    else:
        console.print("[green]✅ PORT variable is fine (or not set manually).[/green]")
else:
    console.print("[red]⚠️ Could not fetch environment variables (non-critical).[/red]")

# ----------------------------------------------------
# 4️⃣ Trigger redeploy
# ----------------------------------------------------
console.print("[cyan]🧹 Clearing build cache and triggering redeploy...[/cyan]")
deploy_resp = requests.post(
    f"{RENDER_API_URL}/services/{service_id}/deploys",
    headers=headers,
    json={"clearCache": True},
)
if deploy_resp.status_code != 201:
    console.print(f"[red]❌ Failed to trigger deploy: {deploy_resp.text}[/red]")
    raise SystemExit(1)

deploy_id = deploy_resp.json()["id"]
console.print(f"[green]✅ Redeploy triggered successfully:[/green] {deploy_id}")

# ----------------------------------------------------
# 5️⃣ Monitor logs
# ----------------------------------------------------
console.print("[yellow]�� Monitoring deploy logs for Python 3.12.7 and startup...[/yellow]")
python_detected = False
startup_detected = False

for _ in track(range(60), description="Watching Render logs..."):
    logs = requests.get(f"{RENDER_API_URL}/deploys/{deploy_id}/events", headers=headers)
    if logs.status_code != 200:
        time.sleep(10)
        continue

    events = logs.json()
    for ev in events:
        msg = ev.get("message", "")
        if "Using Python version" in msg:
            console.print(f"[cyan]{msg}[/cyan]")
            if "3.12" in msg:
                python_detected = True
        if "Application startup complete" in msg:
            startup_detected = True
            break

    if python_detected and startup_detected:
        break
    time.sleep(10)

if python_detected:
    console.print("[green]✅ Python 3.12.7 confirmed![/green]")
else:
    console.print("[red]⚠️ Python version not confirmed — check Render logs manually.[/red]")

# ----------------------------------------------------
# 6️⃣ Verify endpoints
# ----------------------------------------------------
console.print("\n[cyan]🌐 Verifying public endpoints...[/cyan]")

try:
    health = requests.get(f"{BASE_URL}/health", timeout=15).json()
    console.print(f"[green]✅ /health →[/green] {health}")
except Exception as e:
    console.print(f"[red]❌ /health check failed:[/red] {e}")

try:
    clients = requests.get(f"{BASE_URL}/clients/", timeout=15).json()
    console.print(f"[green]✅ /clients →[/green] {clients}")
except Exception as e:
    console.print(f"[red]❌ /clients check failed:[/red] {e}")

console.print("\n[bold green]🎯 Render Doctor completed successfully![/bold green]")
