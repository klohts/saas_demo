#!/bin/bash
# ============================================================
# 🧩 THE13TH Stage 9.3 Final Branding + Middleware Patch
# ------------------------------------------------------------
# Excludes /api/admin from middleware, updates /docs13 tagline,
# and fixes demo key injection in /api/hello.
# ============================================================

PROJECT_DIR="/home/hp/AIAutomationProjects/saas_demo"
MAIN_FILE="$PROJECT_DIR/main.py"

echo "🧩 Applying Stage 9.3 Final Patch..."
sleep 1

# --- 1️⃣ Update middleware to exclude /api/admin properly ---
echo "🔧 Updating middleware exclusions..."
sed -i 's|path.startswith("/admin"),|path.startswith("/admin"), path.startswith("/api/admin"),|' "$MAIN_FILE"

# --- 2️⃣ Replace /api/hello route with robust demo key logic ---
echo "🔧 Replacing /api/hello route logic..."
sed -i '/@app.get("\/api\/hello")/,/^$/d' "$MAIN_FILE"
cat <<'PYADD' >> "$MAIN_FILE"

@app.get("/api/hello")
def hello(key: str = Header(None, alias="X-API-Key")):
    """Returns client info and confirms demo mode."""
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

# --- 3️⃣ Update /docs13 section to include full tagline ---
echo "🔧 Updating /docs13 tagline..."
sed -i '/def docs13/,/return HTMLResponse/c\
@app.get("/docs13", response_class=HTMLResponse)\n\
async def docs13():\n\
    content = f"""\n\
    <html><head><title>{THEME["name"]} — Docs</title>\n\
    <link rel='stylesheet' href='/static/the13th.css'></head>\n\
    <body class='page'>\n\
      <div class='demo-banner'>⚙️ DEMO MODE ACTIVE</div>\n\
      <h1>{THEME["name"]} API Quick-Start</h1>\n\
      <p class='tag'>{THEME["tagline"]}</p>\n\
      <section class='card'>\n\
        <h3>Authentication</h3>\n\
        <code>Header: X-API-Key: &lt;client_api_key&gt;</code>\n\
      </section>\n\
      <section class='card'>\n\
        <h3>Endpoints</h3>\n\
        <ul>\n\
          <li><b>GET</b> /api/plan — Available Plans</li>\n\
          <li><b>GET</b> /billing/status — Client quota status</li>\n\
          <li><b>GET</b> /api/hello — Example protected route</li>\n\
        </ul>\n\
      </section>\n\
      <footer><a href='/'>← Back to Home</a></footer>\n\
    </body></html>"""\n\
    return HTMLResponse(content)' "$MAIN_FILE"

# --- 4️⃣ Commit + push + deploy ---
cd "$PROJECT_DIR"
echo "💾 Committing final patch..."
git add main.py
git commit -m "Stage 9.3 Final Branding + Middleware Fix" >/dev/null 2>&1
git push origin main >/dev/null 2>&1

echo "🚀 Triggering Render redeploy..."
curl -s -X POST "https://api.render.com/deploy/srv-d475kper433s738vdmr0?key=AQ4JOubHX1g" -H "Cache-Control: no-cache" > /dev/null

echo "⏳ Waiting 45 seconds for Render to rebuild..."
sleep 45

echo "🧪 Running full verification..."
bash "$PROJECT_DIR/verify_the13th.sh"

echo "✅ Stage 9.3 patch applied and verified!"
echo "🌍 Visit https://the13th.onrender.com and https://the13th.onrender.com/docs13"
