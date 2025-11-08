#!/bin/bash
# ============================================================
# 🧩 THE13TH Stage 9.5 Demo Key Persistence Patch
# ------------------------------------------------------------
# Ensures demo client is always created and key stored
# persistently on Render so /api/hello works every time.
# ============================================================

PROJECT_DIR="/home/hp/AIAutomationProjects/saas_demo"
MAIN_FILE="$PROJECT_DIR/main.py"

echo "🔧 Applying Stage 9.5 Demo Persistence Patch..."
sleep 1

# --- Replace demo key handling in ensure_demo_client() ---
sed -i '/def ensure_demo_client()/,/def hello/d' "$MAIN_FILE"

cat <<'PYADD' >> "$MAIN_FILE"

# --- Demo client bootstrap (persistent storage) ---
def ensure_demo_client():
    """Ensures a demo client exists and persists its API key."""
    clients = cm.list_clients()
    demo_path = os.path.join(APP_ROOT, "data", "demo_api_key.txt")
    if not clients:
        logging.info("🧩 Creating demo client (fresh instance)...")
        demo = cm.create_client("Demo Client", "Free")
        os.makedirs(os.path.dirname(demo_path), exist_ok=True)
        with open(demo_path, "w") as f:
            f.write(demo["api_key"])
        logging.info(f"✅ Demo client created with API key: {demo['api_key']}")
    elif not os.path.exists(demo_path):
        # recover key from first client if exists
        demo = clients[0]
        os.makedirs(os.path.dirname(demo_path), exist_ok=True)
        with open(demo_path, "w") as f:
            f.write(demo["api_key"])
        logging.info(f"♻️ Restored demo key from DB: {demo['api_key']}")
    else:
        logging.info("🟣 Demo client already exists; skipping creation.")

if DEMO_MODE:
    ensure_demo_client()

# --- /api/hello route (with persistent demo key fallback) ---
@app.get("/api/hello")
def hello(key: str = Header(None, alias="X-API-Key")):
    """Returns client info and confirms demo mode."""
    demo_path = os.path.join(APP_ROOT, "data", "demo_api_key.txt")
    if DEMO_MODE and (not key) and os.path.exists(demo_path):
        key = open(demo_path).read().strip()
    if not key:
        raise HTTPException(status_code=401, detail="X-API-Key header required.")
    c = cm.get_client_by_api(key)
    if not c:
        raise HTTPException(status_code=401, detail="Invalid or missing demo key.")
    return {"message": f"hello {c['name']}", "plan": c['plan'], "demo_mode": DEMO_MODE}
PYADD

# --- Commit + Deploy ---
cd "$PROJECT_DIR"
git add main.py
git commit -m "Stage 9.5: Persistent demo key storage for demo mode" >/dev/null 2>&1
git push origin main >/dev/null 2>&1

echo "🚀 Triggering Render redeploy..."
curl -s -X POST "https://api.render.com/deploy/srv-d475kper433s738vdmr0?key=AQ4JOubHX1g" -H "Cache-Control: no-cache" > /dev/null

echo "⏳ Waiting 50 seconds for Render rebuild..."
sleep 50

echo "�� Running post-deploy verification..."
bash "$PROJECT_DIR/verify_the13th.sh"

echo "✅ Stage 9.5 patch applied successfully!"
echo "🌍 Visit https://the13th.onrender.com once Render completes."
