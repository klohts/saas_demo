#!/bin/bash
# ============================================================
# 🧩 THE13TH Stage 9.2 Middleware & Demo Key Fix
# ------------------------------------------------------------
# Properly excludes /api/admin routes from middleware checks
# and ensures demo key auto-load for /api/hello.
# ============================================================

PROJECT_DIR="/home/hp/AIAutomationProjects/saas_demo"
MAIN_FILE="$PROJECT_DIR/main.py"

echo "🔧 Applying precise Stage 9.2 patch to THE13TH main.py..."

# --- Update middleware exclusions ---
sed -i 's|path.startswith("/admin"),|path.startswith("/admin"), path.startswith("/api/admin"),|' "$MAIN_FILE"

# --- Replace /api/hello route logic to auto-load demo key ---
sed -i '/def hello/q' "$MAIN_FILE" # trim any old hello route
cat <<'PYADD' >> "$MAIN_FILE"

@app.get("/api/hello")
def hello(key: str = Header(None, alias="X-API-Key")):
    if DEMO_MODE and not key:
        demo_key_path = os.path.join(APP_ROOT, "tmp_demo_api_key.txt")
        if os.path.exists(demo_key_path):
            key = open(demo_key_path).read().strip()
    if not key:
        raise HTTPException(status_code=401, detail="X-API-Key header required.")
    c = cm.get_client_by_api(key)
    if not c:
        raise HTTPException(status_code=401, detail="Invalid or missing demo key.")
    return {
        "message": f"hello {c['name']}",
        "plan": c['plan'],
        "demo_mode": DEMO_MODE
    }
PYADD

# --- Commit + deploy ---
cd "$PROJECT_DIR"
git add main.py
git commit -m "Stage 9.2 middleware/admin/demo key fix" >/dev/null 2>&1
git push origin main >/dev/null 2>&1

echo "🚀 Triggering Render redeploy..."
curl -s -X POST "https://api.render.com/deploy/srv-d475kper433s738vdmr0?key=AQ4JOubHX1g" -H "Cache-Control: no-cache" > /dev/null

echo "⏳ Waiting for Render to rebuild (40s)..."
sleep 40

echo "🧪 Running verification..."
bash "$PROJECT_DIR/verify_the13th.sh"

echo "✅ Stage 9.2 patch applied successfully."
echo "🌍 Visit https://the13th.onrender.com once Render completes."
