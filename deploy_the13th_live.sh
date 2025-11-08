#!/bin/bash
# ============================================================
# 🚀 THE13TH Smart Deploy Script (v4.8.x Final)
# ------------------------------------------------------------
# Pushes latest code to GitHub, triggers Render deploy hook,
# polls live status via Render API until "live" or "failed",
# then runs post-deploy verification.
#
# Author: Ken | Project: THE13TH
# ============================================================

# --- Config ---
SERVICE_ID="srv-d475kper433s738vdmr0"
DEPLOY_HOOK="https://api.render.com/deploy/srv-d475kper433s738vdmr0?key=AQ4JOubHX1g"
RENDER_API="https://api.render.com/v1"
PROJECT_DIR="/home/hp/AIAutomationProjects/saas_demo"

# 🧩 IMPORTANT: set your Render API key here (for status polling)
# Generate one at: https://render.com/docs/api
export RENDER_API_KEY=rnd_EsPVNUxZqMcSI7q9GyODBMaRzHXd

# --- Start ---
echo "🚀 Starting THE13TH smart deploy..."
cd "$PROJECT_DIR" || { echo "❌ Project directory not found!"; exit 1; }

# --- Git push (with empty commit if no changes) ---
echo "🔄 Checking for local changes..."
git add .
if git diff-index --quiet HEAD --; then
  git commit --allow-empty -m "Force redeploy $(date '+%Y-%m-%d %H:%M:%S')" >/dev/null 2>&1
  echo "ℹ️  No local file changes; forcing new deploy commit."
else
  git commit -m "Auto-deploy $(date '+%Y-%m-%d %H:%M:%S')" >/dev/null 2>&1
  echo "✅ Committed new changes."
fi

git push origin main >/dev/null 2>&1
echo "✅ Code pushed to GitHub (main)."

# --- Trigger Render Deploy ---
echo "🚀 Triggering Render deployment..."
DEPLOY_ID=$(curl -s -X POST "$DEPLOY_HOOK" | grep -oE '"id":"[^"]+' | cut -d'"' -f4)

if [ -z "$DEPLOY_ID" ]; then
  echo "❌ Failed to trigger deploy. Check deploy hook or network."
  exit 1
fi

echo "📦 Deployment ID: $DEPLOY_ID"
APP_URL="https://the13th.onrender.com"
echo "🌍 App URL: $APP_URL"

# --- Poll until live or failed ---
echo "⏳ Waiting for Render to build..."
sleep 10

while true; do
  STATUS=$(curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
    "${RENDER_API}/deploys/${DEPLOY_ID}" | grep -oE '"status":"[^"]+' | cut -d'"' -f4)

  case "$STATUS" in
    live)
      echo "✅ Deployment successful! THE13TH is now live:"
      echo "   🌍 $APP_URL"
      break
      ;;
    failed)
      echo "❌ Deployment failed. Check Render logs for details."
      exit 1
      ;;
    canceled)
      echo "⚠️  Render labeled this deploy as canceled (duplicate SHA)."
      echo "🔎 Checking for latest active deploy..."
      LATEST_DEPLOY=$(curl -s -H "Authorization: Bearer $RENDER_API_KEY" \
        "${RENDER_API}/services/${SERVICE_ID}/deploys" | grep -m1 -oE '"id":"[^"]+' | cut -d'"' -f4)
      if [ "$LATEST_DEPLOY" != "$DEPLOY_ID" ]; then
        echo "↪️  Switching to latest deploy: $LATEST_DEPLOY"
        DEPLOY_ID=$LATEST_DEPLOY
      fi
      sleep 15
      ;;
    build_in_progress|update_in_progress|created|pre_deploy_in_progress|queued)
      echo "🛠️  Build in progress... rechecking in 15s."
      sleep 15
      ;;
    *)
      echo "⏸️  Waiting... current status: ${STATUS:-unknown}"
      sleep 15
      ;;
  esac
done

# --- Verify after live status ---
echo "🔎 Running THE13TH verification..."
bash "$PROJECT_DIR/verify_the13th.sh"

echo "🧭 Deployment & verification complete!"
echo "✨ THE13TH is live at: $APP_URL"
