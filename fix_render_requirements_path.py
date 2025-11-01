"""
fix_render_requirements_path.py

Ensures Render installs dependencies correctly by:
✅ Moving requirements.txt to repo root if needed
✅ Updating render.yaml buildCommand
✅ Committing + pushing automatically
"""

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_ROOT.parent
RENDER_YAML = PROJECT_ROOT / "render.yaml"
REQ_FILE = PROJECT_ROOT / "requirements.txt"
REQ_TARGET = REPO_ROOT / "requirements.txt"

print("🚀 Fixing Render requirements path...")

# 1️⃣ Move requirements.txt if inside saas_demo/
if REQ_FILE.exists():
    print(f"🧩 Moving requirements.txt from {REQ_FILE} → {REQ_TARGET}")
    content = REQ_FILE.read_text()
    REQ_TARGET.write_text(content)
    REQ_FILE.unlink()
else:
    print("✅ requirements.txt already in correct location.")

# 2️⃣ Update render.yaml build command
if RENDER_YAML.exists():
    yaml_text = RENDER_YAML.read_text()
    if "buildCommand" not in yaml_text or "pip install" not in yaml_text:
        print("🛠️  Adding buildCommand to render.yaml...")
        yaml_text = yaml_text.strip() + "\n\nbuildCommand: pip install -r requirements.txt\n"
        RENDER_YAML.write_text(yaml_text)
    else:
        print("✅ render.yaml already includes buildCommand.")
else:
    print("⚠️ render.yaml not found! Creating one.")
    yaml_text = """services:
  - type: web
    name: saas-demo
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn saas_demo.app.main:app --host 0.0.0.0 --port $PORT
"""
    RENDER_YAML.write_text(yaml_text)

# 3️⃣ Commit and push
try:
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "commit", "-m", "Fix: ensure Render installs requirements from repo root"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("✅ Changes committed and pushed.")
except subprocess.CalledProcessError:
    print("⚠️ Git commit/push failed or nothing to commit.")

print("\n🎯 Done!")
print("Next steps:")
print("1️⃣ Wait for Render to auto-redeploy.")
print("2️⃣ Check logs — you should now see:")
print("   ==> Running build command 'pip install -r requirements.txt'")
print("3️⃣ Then confirm with:")
print("   curl https://ai-email-bot-0xut.onrender.com/health")
print("   curl https://ai-email-bot-0xut.onrender.com/clients/")
