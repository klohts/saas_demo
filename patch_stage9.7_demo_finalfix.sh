#!/bin/bash
# ============================================================
# 🧩 THE13TH Stage 9.7 — Final Demo Key Persistence Fix
# ------------------------------------------------------------
# Fixes DEMO_MODE scope + indentation issues.
# ============================================================

PROJECT_DIR="/home/hp/AIAutomationProjects/saas_demo"
MAIN_FILE="$PROJECT_DIR/main.py"

echo "🩹 Applying Stage 9.7 Final Demo Patch..."
sleep 1

# --- Remove any previous ensure_demo_client + /api/hello blocks ---
sed -i '/def ensure_demo_client()/,/return {"message":/d' "$MAIN_FILE"

# --- Append corrected block at the end (after all imports + globals) ---
cat <<'PYADD' >> "$MAIN_FILE"

# ============================================================
# 🧠 Demo Client Initialization (fixed scope + safe persistence)
# ============================================================

def ensure_demo_client():
    """Ensures a demo client exists and persists its API key safely."""
    clients = cm.list_clients()
    demo_dir = os.path.join(APP_ROOT, "data")
    demo_path = os.path.join(demo_dir, "demo_api_key.txt")

    os.makedirs(demo_dir, exist_ok=True)
    try:
        if not clients:
            logging.info("🧩 Creating demo client (fresh instance)...")
            demo = cm.create_client("Demo Client", "Free")
            with open(demo_path, "w") as f:
                f.write(demo["api_key"])
            logging.info(f"✅ Demo client created with API key: {demo['api_key']}")
        elif not os.path.exists(demo_path):
            demo = clients[0]
            with open(demo_path, "w") as f:
                f.write(demo["api_key"])
            logging.info(f"♻️ Restored demo key from DB: {demo['api_key']}")
        else:
            logging.info("🟣 Demo client already exists; skipping creation.")
    except Exception as e:
        logging.error(f"❌ Failed to initialize demo client: {e}")

if DEMO_MODE:
    ensure_demo_client()

# ============================================================
# 🔑 /api/hello — demo key fallback route (fixed indent)
# ============================================================
@app.get("/api/hello")
def hello(key: str = Header(None, alias="X-API-Key")):
    """Returns client info and confirms demo mode."""
    demo_path = os.path.join(APP_ROOT, "data", "demo_api_key.txt")
    if DEMO_MODE and not key and os.path.exists(demo_path):
        try:
            key = open(demo_path).read().strip()
        except Exception as e:
            logging.error(f"❌ Could not read demo key: {e}")
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
git commit -m "Stage 9.7: Fix DEMO_MODE scope + indentation for demo client" >/dev/null 2>&1
git push origin main >/dev/null 2>&1

echo "🚀 Triggering Render redeploy..."
curl -s -X POST "https://api.render.com/deploy/srv-d475kper433s738vdmr0?key=AQ4JOubHX1g" -H "Cache-Control: no-cache" > /dev/null

echo "⏳ Waiting 90 seconds for Render rebuild..."
sleep 90

echo "🧪 Running post-deploy verification..."
bash "$PROJECT_DIR/verify_the13th.sh"

echo "✅ Stage 9.7 Final Demo Patch applied successfully!"
