"""
render_ready.py

Ken’s all-in-one Render readiness utility 🚀

✅ Deletes redundant scripts (sync_requirements.py, verify_and_rebuild_deps.py)
✅ Reads current venv packages (pip freeze)
✅ Ensures essential Render dependencies (SQLAlchemy, psycopg2, FastAPI, etc.)
✅ Syncs requirements.txt (deduped, sorted, up-to-date)
✅ Installs locally to verify
✅ Auto-commits changes for push

Usage:
    python render_ready.py
"""

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
REQ_PATH = PROJECT_ROOT / "requirements.txt"

# 🔹 Files to clean up
OLD_SCRIPTS = [
    PROJECT_ROOT / "sync_requirements.py",
    PROJECT_ROOT / "verify_and_rebuild_deps.py",
]

# 🔹 Core dependencies required for Render
REQUIRED_PACKAGES = {
    "fastapi",
    "uvicorn",
    "sqlalchemy",
    "psycopg2-binary",
    "pydantic",
    "python-dotenv",
    "requests",
    "jinja2",
    "loguru",
    "email-validator",
    "python-multipart"
}

print("🚀 Starting Render readiness check...\n")

# --- 1️⃣ Clean up redundant helper scripts ---
for script in OLD_SCRIPTS:
    if script.exists():
        script.unlink()
        print(f"🧹 Deleted old script: {script.name}")
print("✅ Cleanup complete.\n")

# --- 2️⃣ Gather installed packages from venv ---
print("🔍 Collecting installed packages from pip freeze...")
installed_output = subprocess.check_output(["pip", "freeze"], text=True).strip().splitlines()
installed_pkgs = {line.split("==")[0].lower(): line for line in installed_output if "==" in line}
print(f"✅ Found {len(installed_pkgs)} installed packages.\n")

# --- 3️⃣ Ensure requirements.txt exists ---
if not REQ_PATH.exists():
    print("⚠️ No requirements.txt found — creating one.")
    REQ_PATH.touch()

# --- 4️⃣ Read current requirements.txt ---
existing_lines = [l.strip() for l in REQ_PATH.read_text().splitlines() if l.strip() and not l.startswith("#")]
existing_pkgs = {l.split("==")[0].lower(): l for l in existing_lines if "==" in l}

# --- 5️⃣ Determine missing or outdated dependencies ---
missing = []
for pkg in REQUIRED_PACKAGES:
    if pkg not in existing_pkgs:
        missing.append(pkg)
if missing:
    print(f"🧩 Adding {len(missing)} missing Render-critical packages:")
    for pkg in sorted(missing):
        print(f"   + {pkg}")
        if pkg in installed_pkgs:
            existing_lines.append(installed_pkgs[pkg])
        else:
            existing_lines.append(pkg)
else:
    print("✅ All core Render dependencies are present.\n")

# --- 6️⃣ Merge installed + existing + required ---
all_pkgs = {**installed_pkgs, **existing_pkgs}
combined_lines = sorted(set(all_pkgs.values()), key=lambda x: x.lower())

# --- 7️⃣ Write back to requirements.txt ---
REQ_PATH.write_text("\n".join(combined_lines) + "\n")
print("✅ requirements.txt synced, deduplicated, and updated.\n")

# --- 8️⃣ Install locally to verify ---
print("📦 Verifying by installing locally...")
subprocess.run(["pip", "install", "-r", str(REQ_PATH)], check=True)
print("✅ Local install verification complete.\n")

# --- 9️⃣ Git commit ---
try:
    subprocess.run(["git", "add", "requirements.txt"], check=True)
    subprocess.run(
        ["git", "commit", "-m", "Render Ready: sync dependencies, clean scripts, verify install"],
        check=True,
    )
    print("✅ Git commit created successfully.\n")
except subprocess.CalledProcessError:
    print("⚠️ No new changes to commit (repo clean).\n")

print("🎯 DONE!")
print("Next steps:")
print("1️⃣ Run: git push")
print("2️⃣ Wait for Render to redeploy automatically")
print("3️⃣ Test your app with:")
print("   curl https://ai-email-bot-0xut.onrender.com/health")
print("   curl https://ai-email-bot-0xut.onrender.com/clients/\n")

print("✨ Your project is now Render-ready and dependency-proof!")
