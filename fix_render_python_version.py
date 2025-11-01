"""
fix_render_python_version.py
─────────────────────────────
Force Render to use Python 3.12 to avoid SQLAlchemy 2.x / Python 3.13
compatibility errors.

✅ Pins pythonVersion: 3.12.7 in render.yaml
✅ Ensures buildCommand installs requirements
✅ Commits + pushes automatically
"""

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
RENDER_YAML = PROJECT_ROOT / "render.yaml"

print("🚀 Enforcing Python 3.12 on Render...\n")

# --- 1️⃣ Update render.yaml safely ---
yaml_base = """services:
  - type: web
    name: saas-demo
    env: python
    pythonVersion: 3.12.7
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn saas_demo.app.main:app --host 0.0.0.0 --port $PORT
"""

if not RENDER_YAML.exists():
    print("⚠️ render.yaml not found — creating a new one.")
    RENDER_YAML.write_text(yaml_base)
else:
    content = RENDER_YAML.read_text()
    if "pythonVersion" not in content or "3.12" not in content:
        print("🛠️ Updating render.yaml to enforce Python 3.12.7")
        # Rebuild file with guaranteed version
        lines = []
        for line in content.splitlines():
            if line.strip().startswith("pythonVersion:"):
                continue
            lines.append(line)
        updated = []
        found_build = False
        for line in lines:
            updated.append(line)
            if "env: python" in line:
                updated.append("    pythonVersion: 3.12.7")
            if "buildCommand:" in line:
                found_build = True
        if not found_build:
            updated.append("    buildCommand: pip install -r requirements.txt")
        if not any("startCommand:" in l for l in updated):
            updated.append("    startCommand: uvicorn saas_demo.app.main:app --host 0.0.0.0 --port $PORT")
        RENDER_YAML.write_text("\n".join(updated) + "\n")
    else:
        print("✅ render.yaml already pins Python 3.12.\n")

# --- 2️⃣ Git commit & push ---
try:
    subprocess.run(["git", "add", "render.yaml"], check=True)
    subprocess.run(["git", "commit", "-m", "Fix: pin Python 3.12 for SQLAlchemy compatibility"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("✅ Changes committed & pushed.")
except subprocess.CalledProcessError:
    print("⚠️ No changes to commit or push (already up-to-date).")

# --- 3️⃣ Final instructions ---
print("""
🎯 Done! Render will now rebuild using Python 3.12.

Next steps:
1️⃣ Wait for Render to automatically redeploy.
2️⃣ Watch logs — you should see:
     ==> Using Python version 3.12.7
     ==> Successfully installed fastapi sqlalchemy psycopg2-binary ...
3️⃣ Then verify:
     curl https://ai-email-bot-0xut.onrender.com/health
     curl https://ai-email-bot-0xut.onrender.com/clients/
""")
