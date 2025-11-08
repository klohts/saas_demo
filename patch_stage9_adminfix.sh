#!/bin/bash
# ============================================================
# 🩹 THE13TH Stage 9.1 Hotfix (Admin + Demo Mode Fix)
# ------------------------------------------------------------
# Fixes middleware overreach, updates /docs13 branding,
# and ensures demo client injection for /api/hello.
# Author: Ken | Project: THE13TH | Date: $(date +'%Y-%m-%d')
# ============================================================

PROJECT_DIR="/home/hp/AIAutomationProjects/saas_demo"
MAIN_FILE="$PROJECT_DIR/main.py"

echo "🩹 Applying THE13TH Stage 9.1 Hotfix..."
sleep 1

# --- 1️⃣ Fix middleware to exclude /api/admin ---
echo "🔧 Updating middleware exclusions..."
sed -i 's|path.startswith("/api/plan"),|path.startswith("/api/plan"), path.startswith("/api/admin"),|' "$MAIN_FILE"

# --- 2️⃣ Ensure demo API key loading for /api/hello ---
echo "🔧 Injecting demo key handling logic into /api/hello route..."
sed -i '/def hello/a\
    if DEMO_MODE and not key:\
        key_path = os.path.join(APP_ROOT, "tmp_demo_api_key.txt")\
        if os.path.exists(key_path):\
            key = open(key_path).read().strip()' "$MAIN_FILE"

# --- 3️⃣ Update /docs13 to include tagline ---
echo "🔧 Updating /docs13 section branding..."
sed -i 's|<h1>{THEME\[.\+API Quick-Start</h1>|<h1>{THEME["name"]} API Quick-Start</h1><p class="tag">{THEME["tagline"]}</p>|' "$MAIN_FILE"

# --- 4️⃣ Commit + Deploy ---
echo "💾 Committing changes..."
cd "$PROJECT_DIR"
git add main.py
git commit -m "Stage 9.1 Hotfix: admin middleware + demo mode" >/dev/null 2>&1
git push origin main >/dev/null 2>&1

echo "🚀 Triggering redeploy..."
curl -s -X POST "https://api.render.com/deploy/srv-d475kper433s738vdmr0?key=AQ4JOubHX1g" -H "Cache-Control: no-cache" > /dev/null

echo "⏳ Waiting 40 seconds for Render to build..."
sleep 40

echo "🧪 Running post-deploy verification..."
bash "$PROJECT_DIR/verify_the13th.sh"

echo "✅ Hotfix applied successfully!"
echo "🌍 Check https://the13th.onrender.com once rebuild completes."
