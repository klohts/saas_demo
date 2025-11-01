"""
Auto-fix Render import errors for nested FastAPI apps.

✅ Converts all relative imports (e.g. `from .database import engine`)
   to absolute imports (e.g. `from saas_demo.app.database import engine`)

✅ Ensures `saas_demo/__init__.py` exists
✅ Commits and stages all changes

Run this from your project root:
    python fix_render_imports.py
"""

import os
import re
import subprocess
from pathlib import Path

# --- CONFIG ---
PACKAGE_ROOT = "saas_demo"
APP_DIR = Path(__file__).resolve().parent / "app"
TARGET_PACKAGE = f"{PACKAGE_ROOT}.app"

print(f"🔧 Starting Render import fixer for package '{TARGET_PACKAGE}'...")

# --- 1️⃣ Ensure saas_demo/__init__.py exists ---
init_file = Path(__file__).resolve().parent / "__init__.py"
if not init_file.exists():
    init_file.touch()
    print(f"✅ Created {init_file.relative_to(Path.cwd())}")
else:
    print("✅ __init__.py already exists at saas_demo/")

# --- 2️⃣ Fix relative imports inside saas_demo/app/*.py recursively ---
def fix_imports_in_file(file_path: Path):
    text = file_path.read_text()
    original_text = text

    # Replace lines like: from .database import X
    text = re.sub(
        r"from\s+\.(\S+)\s+import",
        lambda m: f"from {TARGET_PACKAGE}.{m.group(1)} import",
        text,
    )

    # Replace lines like: from . import models
    text = re.sub(
        r"from\s+\.\s+import",
        f"from {TARGET_PACKAGE} import",
        text,
    )

    if text != original_text:
        file_path.write_text(text)
        print(f"🛠️  Updated imports in {file_path.relative_to(Path.cwd())}")
        return True
    return False

changed_files = []
for pyfile in APP_DIR.rglob("*.py"):
    if "fix_render_imports.py" in str(pyfile):
        continue
    if fix_imports_in_file(pyfile):
        changed_files.append(pyfile)

if not changed_files:
    print("✅ No relative imports found. Nothing to update.")
else:
    print(f"\n✅ Fixed imports in {len(changed_files)} files.\n")

# --- 3️⃣ Stage and commit changes ---
try:
    subprocess.run(["git", "add", "."], check=True)
    subprocess.run(
        ["git", "commit", "-m", "Fix: update imports for Render deployment"], check=True
    )
    print("✅ Changes committed successfully.")
except subprocess.CalledProcessError:
    print("⚠️ Git commit failed — check if there were no changes or repo is clean.")

print("\n🎯 Done! Next steps:")
print("1️⃣ git push")
print("2️⃣ Wait for Render to redeploy automatically")
print("3️⃣ Test with:")
print("   curl https://ai-email-bot-0xut.onrender.com/health")
print("   curl https://ai-email-bot-0xut.onrender.com/clients/")
