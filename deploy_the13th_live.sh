#!/bin/bash
# ============================================================
# 🚀 THE13TH Smart Deploy Script  — Stage 10  (Final)
# ------------------------------------------------------------
# Pushes code → triggers Render deploy hook → polls live status
# Works with either JSON or “Accepted” responses.
# ============================================================

SERVICE_ID="srv-d475kper433s738vdmr0"
DEPLOY_HOOK="https://api.render.com/deploy/srv-d475kper433s738vdmr0?key=AQ4JOubHX1g"
RENDER_API="https://api.render.com/v1"
PROJECT_DIR="/home/hp/AIAutomationProjects/saas_demo"
APP_URL="https://the13th.onrender.com"

# 🧩  Add your Render API key here for status polling
export RENDER_API_KEY="rnd_XXXXXXXXXXXXXXXXXXXXXXXX"

echo "🚀 Starting THE13TH Stage 10 deploy..."
cd "$PROJECT_DIR" || { echo "❌ Project directory not found!"; exit 1; }

# --- Git push (force empty commit if needed) ---
git add .
if git diff-index --quiet HEAD --; then
  git commit --allow-empty -m "Force redeploy $(date '+%Y-%m-%d %H:%M:%S')" >/dev/null 2>&1
  echo "ℹ️  No local changes; forced empty commit."
else
  git commit -m "Auto-deploy $(date '+%Y-%m-%d %H:%M:%S')" >/dev/null 2>&1
  echo "✅ Committed code changes."
fi
git push origin main >/dev/null 2>&1
echo "✅ Code pushed to GitHub (main)."

# --- Trigger deploy hook ---
echo "🚀 Triggering Render deployment..."
RESPONSE=$(command curl -s -X POST "$DEPLOY_HOOK")
echo "🔍 Deploy-hook raw response: $RESPONSE"

# Parse ID or fallback to Accepted
if echo "$RESPONSE" | grep -qi '"id"'; then
  DEPLOY_ID=$(echo "$RESPONSE" | grep -oE '"id":"[^"]+' | cut -d'"' -f4)
  echo "📦 Deploy ID detected: $DEPLOY_ID"
elif echo "$RESPONSE" | grep -qi "accepted"; then
  echo "✅ Render accepted deploy request (202 Accepted)."
  DEPLOY_ID=""
else
  echo "❌ Deploy hook returned unexpected response. Aborting."
  exit 1
fi

# --- Determine deploy ID if missing (Accepted case) ---
if [ -z "$DEPLOY_ID" ]; then
  echo "🔎 Fetching latest active deploy for this service..."
  DEPLOY_ID=$(command curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
      "${RENDER_API}/services/${SERVICE_ID}/deploys" \
      | grep -m1 -oE '"id":"[^"]+' | cut -d'"' -f4)
  echo "📦 Using latest deploy ID: $DEPLOY_ID"
fi

# --- Poll until live/failed ---
echo "⏳ Waiting for Render to build..."
sleep 10
while true; do
  STATUS=$(command curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
    "${RENDER_API}/deploys/${DEPLOY_ID}" | grep -oE '"status":"[^"]+' | cut -d'"' -f4)

  case "$STATUS" in
    live)
      echo "✅ Deployment successful! THE13TH is live at:"
      echo "   🌍  $APP_URL"
      break ;;
    failed)
      echo "❌ Deployment failed. Check Render logs."
      exit 1 ;;
    canceled)
      echo "⚠️  Deploy marked canceled (duplicate SHA). Checking latest..."
      DEPLOY_ID=$(command curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
        "${RENDER_API}/services/${SERVICE_ID}/deploys" \
        | grep -m1 -oE '"id":"[^"]+' | cut -d'"' -f4)
      sleep 20 ;;
    build_in_progress|update_in_progress|created|pre_deploy_in_progress|queued)
      echo "🛠️  Build in progress... rechecking in 15 s."
      sleep 15 ;;
    *)
      echo "⏸️  Waiting... current status: ${STATUS:-unknown}"
      sleep 15 ;;
  esac
done

# --- Verification ---
echo "🔎 Running THE13TH verification..."
bash "$PROJECT_DIR/verify_the13th.sh"

echo "🧭 Deployment & verification complete!"
echo "✨ THE13TH is live at: $APP_URL"
