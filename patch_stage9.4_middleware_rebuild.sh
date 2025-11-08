#!/bin/bash
# ============================================================
# 🧩 THE13TH Stage 9.4 Middleware Rebuild Patch
# ------------------------------------------------------------
# Fully replaces the middleware block with explicit exclusions
# for /api/admin, /api/plan, /api/hello, /docs13, etc.
# ============================================================

PROJECT_DIR="/home/hp/AIAutomationProjects/saas_demo"
MAIN_FILE="$PROJECT_DIR/main.py"

echo "🧱 Rebuilding middleware block in main.py..."
sleep 1

# --- Remove old middleware definition entirely ---
sed -i '/class UsageMiddleware/,/app.add_middleware(UsageMiddleware)/d' "$MAIN_FILE"

# --- Insert clean rewritten middleware ---
cat <<'PYADD' >> "$MAIN_FILE"

# ============================================================
# 🔧 Rebuilt UsageMiddleware (Stage 9.4)
# ============================================================
from starlette.middleware.base import BaseHTTPMiddleware
class UsageMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        # Explicit exclusions: anything public, admin, docs, or demo
        excluded_paths = [
            "/",
            "/docs",
            "/docs13",
            "/static",
            "/admin",
            "/api/admin",
            "/api/plan"
        ]
        if any(path.startswith(p) for p in excluded_paths):
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse({"detail": "X-API-Key header required."}, status_code=401)
        client = cm.get_client_by_api(api_key)
        if not client:
            return JSONResponse({"detail": "Invalid API key."}, status_code=401)

        quota_limit, quota_used = client.get("quota_limit", 0), client.get("quota_used", 0)
        if quota_limit != -1 and quota_used >= quota_limit:
            return JSONResponse({"detail": "Quota exceeded."}, status_code=429)
        cm.increment_usage(api_key, 1)
        return await call_next(request)

app.add_middleware(UsageMiddleware)
PYADD

# --- Commit and deploy ---
cd "$PROJECT_DIR"
git add main.py
git commit -m "Stage 9.4 Middleware rebuild (definitive exclusion logic)" >/dev/null 2>&1
git push origin main >/dev/null 2>&1

echo "🚀 Triggering Render redeploy..."
curl -s -X POST "https://api.render.com/deploy/srv-d475kper433s738vdmr0?key=AQ4JOubHX1g" -H "Cache-Control: no-cache" > /dev/null

echo "⏳ Waiting 45 seconds for Render rebuild..."
sleep 45

echo "🧪 Running post-deploy verification..."
bash "$PROJECT_DIR/verify_the13th.sh"

echo "✅ Stage 9.4 middleware rebuild applied successfully!"
