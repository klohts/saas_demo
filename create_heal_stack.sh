#!/usr/bin/env bash
set -e

echo "🧠 Creating self-healing stack..."

# 1. Watchdog
cat > watchdog.py << 'WATCHDOG'
import time, subprocess, sys

def run_fix():
    print("🧠 Running automatic repair...")
    subprocess.run([sys.executable, "fix_all.py"])

def start_server():
    return subprocess.Popen(
        ["uvicorn", "main:app", "--reload"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

while True:
    print("🚀 Starting server with watchdog...")
    p = start_server()
    for line in p.stdout:
        print(line, end="")
        if "Traceback" in line or "Exception" in line or "Error" in line:
            print("🚨 Crash detected!")
            p.kill()
            run_fix()
            break
    time.sleep(2)
WATCHDOG

# 2. Repair TUI
cat > fix_tui.py << 'TUI'
import subprocess, os, time

def run(cmd):
    print(f"\n$ {cmd}")
    subprocess.run(cmd, shell=True)

while True:
    print("""
┌────────────────────── THE13TH Repair Console ─────────────────────┐
1) Run full auto-fix now
2) Restart server
3) Rebuild database schema
4) Re-pin ENV password hash
5) View server logs (last 200 lines)
6) Git commit + push
7) Tail server logs live
0) Exit
└───────────────────────────────────────────────────────────────────┘
""")

    c = input("Select option: ")

    if c == "1": run("python3 fix_all.py")
    elif c == "2": run("pkill -f uvicorn; uvicorn main:app --reload &")
    elif c == "3": run("python3 fix_all.py")
    elif c == "4": run("python3 fix_all.py")
    elif c == "5": run("tail -n 200 uvicorn_fix.log")
    elif c == "6": run("git add . && git commit -m 'repair' && git push")
    elif c == "7": run("tail -f uvicorn_fix.log")
    elif c == "0": print("👋 Exiting"); break
    else: print("Invalid")
    time.sleep(1)
TUI

# 3. GitHub Action
mkdir -p .github/workflows
cat > .github/workflows/predeploy-fix.yml << 'GHA'
name: Pre-Deploy Auto-Fix

on:
  push:
    branches: [ "main" ]

jobs:
  repair:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.12"
      - name: Run fix script
        run: |
          pip install -r requirements.txt || true
          python3 fix_all.py
      - name: Commit autofixes (if any)
        run: |
          git config user.name "AutoFix Bot"
          git config user.email "autofix@the13th.ai"
          git add .
          git commit -m "chore: auto-repair before deploy" || echo "No changes"
          git push || true
GHA

# 4. Dockerfile health + auto-repair
if [ ! -f Dockerfile ]; then
  echo "Creating Dockerfile..."
  cat > Dockerfile << 'DOCKER'
FROM python:3.12
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt || true

HEALTHCHECK --interval=20s --timeout=10s --retries=3 CMD curl -f http://localhost:8000/admin/login || exit 1
CMD ["python3", "-c", "import os; os.system('python3 fix_all.py'); os.execvp('uvicorn', ['uvicorn','main:app','--host','0.0.0.0','--port','8000'])"]
DOCKER
else
  echo "Patching Dockerfile..."
  grep -q "HEALTHCHECK" Dockerfile || echo 'HEALTHCHECK --interval=20s --timeout=10s --retries=3 CMD curl -f http://localhost:8000/admin/login || exit 1' >> Dockerfile
  grep -q "fix_all.py" Dockerfile || echo 'CMD ["python3", "-c", "import os; os.system('\''python3 fix_all.py'\''); os.execvp('\''uvicorn'\'', ['\''uvicorn'\'','\''main:app'\'','\''--host'\'','\''0.0.0.0'\'','\''--port'\'','\''8000'\''])"]' >> Dockerfile
fi

echo "✅ Heal stack created successfully."
echo "Run with:"
echo "  python3 watchdog.py   (auto-heal server)"
echo "  python3 fix_tui.py    (interactive repairs)"
