#!/bin/bash
echo "🔧 Applying Stage 13.6.2-fix — Add missing Path import to main.py..."

# Ensure 'Path' imported globally
if ! grep -q "from pathlib import Path" main.py; then
  sed -i '/import os/a from pathlib import Path' main.py
  echo "✅ Added 'from pathlib import Path' to main.py"
fi

# Ensure reset_logs function safely handles missing files
sed -i '/def reset_logs/,/return/{s/for f in Path("logs").glob("*.log"):/for f in Path("logs").glob("*.log") if f.exists():/}' main.py

git add main.py
git commit -m "Stage 13.6.2-fix — Path import + reset_logs stability"
git push origin main

echo "✅ Patch complete. Restart with: uvicorn main:app --reload"
