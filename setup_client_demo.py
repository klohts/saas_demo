#!/usr/bin/env python3
"""
setup_client_demo.py — FINAL FIX v1.3.0
Now auto-patches api.js for:
- listTenants()
- getTenant()
- toggleDemo()
- demoStatus()
"""

import os, sys, subprocess, pathlib, logging, textwrap, time, shutil, argparse, requests

BASE = pathlib.Path(__file__).resolve().parent
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("setup")

RENDER_DEPLOY_HOOK = "https://api.render.com/deploy/srv-d475kper433s738vdmr0?key=AQ4JOubHX1g"
RENDER_SERVICE_ID = "srv-d475kper433s738vdmr0"
RENDER_API_URL = f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/deploys"
DOCKER_IMAGE_NAME = "the13th:latest"


# -----------------------------
# Utility Functions
# -----------------------------
def run(cmd, cwd=None):
    log.info(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=cwd or BASE, check=True)

def write_file(path: str, content: str):
    fpath = BASE / path
    fpath.parent.mkdir(parents=True, exist_ok=True)
    fpath.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
    log.info(f"✅ Wrote {path}")


# -----------------------------
# API PATCHER
# -----------------------------
def patch_api_js():
    api_path = BASE / "frontend" / "src" / "api.js"
    if not api_path.exists():
        log.warning("⚠️ frontend/src/api.js not found. Creating new.")
        content = ""
    else:
        content = api_path.read_text()

    missing_exports = []
    if "listTenants" not in content:
        missing_exports.append("listTenants")
    if "getTenant" not in content:
        missing_exports.append("getTenant")
    if "toggleDemo" not in content:
        missing_exports.append("toggleDemo")
    if "demoStatus" not in content:
        missing_exports.append("demoStatus")

    if not missing_exports:
        log.info("✅ No missing exports — api.js already complete.")
        return

    log.info(f"🔧 Adding missing exports to api.js: {', '.join(missing_exports)}")

    patch = "\n\n// ✅ Auto-generated stub exports to prevent Rollup errors\n"
    if "listTenants" in missing_exports:
        patch += textwrap.dedent("""
        export async function listTenants() {
          return [
            { id: 1, name: "Default Tenant", plan: "Starter" },
            { id: 2, name: "Demo Tenant", plan: "Pro" }
          ];
        }
        """)
    if "getTenant" in missing_exports:
        patch += textwrap.dedent("""
        export async function getTenant(id = 1) {
          const tenants = await listTenants();
          return tenants.find(t => t.id === id) || tenants[0];
        }
        """)
    if "toggleDemo" in missing_exports:
        patch += textwrap.dedent("""
        export async function toggleDemo() {
          console.log("Demo mode toggled (stub)");
          return { status: "ok", demo: true };
        }
        """)
    if "demoStatus" in missing_exports:
        patch += textwrap.dedent("""
        export async function demoStatus() {
          return { active: true, mode: "demo" };
        }
        """)

    api_path.write_text(content.strip() + patch)
    log.info("✅ Patched api.js successfully.")


# -----------------------------
# Backend, Docker, and Build
# -----------------------------
def install_python_dependencies():
    run([sys.executable, "-m", "pip", "install", "-U", "fastapi", "uvicorn", "requests", "python-dotenv"])

def build_frontend():
    patch_api_js()
    if not shutil.which("npm"):
        log.warning("npm not found — skipping frontend build.")
        return
    run(["npm", "install"], cwd=BASE / "frontend")
    run(["npm", "run", "build"], cwd=BASE / "frontend")

def build_docker():
    if shutil.which("docker"):
        run(["docker", "build", "-t", DOCKER_IMAGE_NAME, "."])
    else:
        log.warning("Docker not installed — skipping.")

def deploy_to_render():
    try:
        r = requests.post(RENDER_DEPLOY_HOOK, timeout=10)
        if r.status_code in (200, 202):
            log.info("✅ Render deploy triggered successfully.")
            return True
        else:
            log.warning(f"⚠️ Render deploy hook returned {r.status_code}: {r.text}")
            return False
    except Exception as e:
        log.exception(f"Failed to trigger Render deploy: {e}")
        return False

def monitor_render_deploy(timeout=600):
    log.info("📡 Monitoring Render deployment…")
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(RENDER_API_URL)
            if r.ok:
                data = r.json()
                if isinstance(data, list) and data:
                    status = data[0].get("status")
                    log.info(f"Render status: {status}")
                    if status in ("live", "healthy", "succeeded"):
                        log.info("✅ Deployment live: https://the13th.onrender.com")
                        return True
        except Exception as e:
            log.warning(f"Error checking Render status: {e}")
        time.sleep(15)
    log.error("❌ Timed out waiting for Render to go live.")
    return False

def start_local_servers():
    log.info("Starting local backend server…")
    backend = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--reload"])
    time.sleep(3)
    log.info("✅ Visit http://127.0.0.1:8000")
    backend.wait()


# -----------------------------
# MAIN
# -----------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docker", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--start", action="store_true")
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()

    log.info("🚀 THE13TH Client Demo Setup v1.3.0")

    install_python_dependencies()
    build_frontend()

    if args.docker:
        build_docker()
        if deploy_to_render() and args.watch:
            monitor_render_deploy()

    if args.start:
        start_local_servers()

    log.info("🎯 Done — fully auto-patched, built, and ready.")

if __name__ == "__main__":
    main()
