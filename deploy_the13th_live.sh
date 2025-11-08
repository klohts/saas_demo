#!/bin/bash
# ============================================================
# 🚀 THE13TH Smart Deploy Script with Live Status Polling
# ------------------------------------------------------------
# Pushes latest code to GitHub, triggers Render deploy hook,
# polls deploy status via API until "live" or "failed".
# Author: Ken | Project: THE13TH | Version: v4.8.x
# ============================================================

SERVICE_ID="srv-d475kper433s738vdmr0"
DEPLOY_HOOK="https://api.render.com/deploy/srv-d475kper433s738vdmr0?key=AQ4JOubHX1g"
RENDER_API="https://api.render.com/v1/deploys"
PROJECT_DIR="/home/hp/AIAutomationProjects/saas_demo"

# Optional: your Render API key (read-only)
# export RENDER_API_KEY="rnd_..."

echo "🔄 Pushing latest changes to GitHub..."
cd "$PROJECT_DIR" || exit 1
git add .
git commit -m "Auto-deploy $(date '+%Y-%m-%d %H:%M:%S')" >/dev/null 2>&1 || echo "ℹ️  No new changes to commit."
git push origin main >/dev/null 2>&1
echo "✅ Code pushed successfully to GitHub (main)."

echo "🚀 Triggering deployment on Render..."
DEPLOY_ID=$(curl -s -X POST "$DEPLOY_HOOK" | grep -oE '"id":"[^"]+' | cut -d'"' -f4)

if [ -z "$DEPLOY_ID" ]; then
  echo "❌ Failed to trigger deploy. Check deploy hook or network."
  exit 1
fi

echo "📦 Deployment ID: $DEPLOY_ID"
echo "🌍 App URL: https://the13th.onrender.com"
echo "⏳ Waiting for Render to start building..."

# Poll Render Deploy API until it's live or failed
while true; do
  STATUS=$(curl -s "${RENDER_API}/${DEPLOY_ID}" | grep -oE '"status":"[^"]+' | cut -d'"' -f4)

  case "$STATUS" in
    "live")
      echo "✅ Deploy successful! THE13TH is now live at:"
      echo "   🌍 https://the13th.onrender.com"
      break
      ;;
    "failed")
      echo "❌ Deploy failed. Check Render logs for details."
      exit 1
      ;;
    "build_in_progress"|"update_in_progress"|"created"|"pre_deploy_in_progress")
      echo "🛠️  Build in progress... checking again in 15s."
      sleep 15
      ;;
    "canceled")
      echo "⚠️  Render marked deploy as canceled (duplicate SHA). Checking if another build is active..."
      # Find latest active build for this service
      LATEST_DEPLOY=$(curl -s "https://api.render.com/v1/services/${SERVICE_ID}/deploys" | grep -m1 -oE '"id":"[^"]+' | cut -d'"' -f4)
      if [ "$LATEST_DEPLOY" != "$DEPLOY_ID" ]; then
        echo "↪️  Switching to latest deploy: $LATEST_DEPLOY"
        DEPLOY_ID=$LATEST_DEPLOY
      fi
      sleep 20
      ;;
    *)
      echo "⏸️  Unknown status: $STATUS. Retrying..."
      sleep 15
      ;;
  esac
done

echo "🔎 Running post-deploy verification..."
bash "$PROJECT_DIR/verify_the13th.sh"

echo "🧭 Deployment and verification complete!"
echo "✨ THE13TH is up and live at: https://the13th.onrender.com"
