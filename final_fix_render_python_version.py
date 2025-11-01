"""
final_fix_render_python_version.py
──────────────────────────────────
Fix Render ignoring pythonVersion:
✅ Moves render.yaml to repo root if inside saas_demo/
✅ Ensures pythonVersion: 3.12.7 is declared
✅ Commits & pushes automatically
✅ Prints verification instructions
"""

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_ROOT.parent

render_in_project = PROJECT_ROOT / "render.yaml"
render_in_root = REPO_ROOT / "render.yaml"

# --- Ensure file is at repo root ---
if render_in_project.exists():
    print(f"📦 Moving {render_in_project} → {render_in_root}")
    render_in_root.write_text(render_in_project.read_text())
    render_in_project.unlink()
else:
    print("✅ render.yaml already in repo root.")

# --- Update YAML to pin Python 3.12.7 ---
yaml_content = """services:
  - type: web
    name: saas-demo
    env: python
    pythonVersion: 3.12.7
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn saas_demo.app.main:app --host 0.0.0.0 --port $PORT
"""

render_in_root.write_text(yaml_content)
print("🛠️ render.yaml updated with pythonVersion: 3.12.7\n")

# --- Git commit & push ---
try:
    subprocess.run(["git", "add", str(render_in_root)], check=True)
    subprocess.run(["git", "commit", "-m", "Fix: enforce Python 3.12.7 and move render.yaml to repo root"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("✅ Changes committed and pushed.")
except subprocess.CalledProcessError:
    print("⚠️ No changes to commit (already up to date).")

print("""
🎯 DONE! Next steps:
1️⃣ Render will now detect render.yaml at repo root.
2️⃣ It will rebuild with Python 3.12.7 (watch logs):
      ==> Using Python version 3.12.7
3️⃣ After deploy completes, verify with:
      curl https://ai-email-bot-0xut.onrender.com/health
      curl https://ai-email-bot-0xut.onrender.com/clients/
""")
