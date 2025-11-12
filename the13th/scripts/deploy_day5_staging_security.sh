#!/usr/bin/env bash
set -e

echo "============================================"
echo "🚀 THE13TH – Day 5: Staging & Security Deploy"
echo "============================================"

cd ~/AIAutomationProjects/saas_demo/the13th

# 1️⃣ Ensure environment file exists
if [ ! -f ".env.production" ]; then
  echo "⚠️  Missing .env.production – creating from example..."
  cp .env.example .env.production
  echo "Please edit .env.production before next deploy."
fi

# 2️⃣ Validate key files
echo "🔍 Checking for Day5 bundle..."
if [ ! -f "Day5_Staging_Security_Bundle.py" ]; then
  echo "❌ Missing Day5_Staging_Security_Bundle.py"
  exit 1
fi

# 3️⃣ Git commit and push
echo "📦 Committing Day 5 security bundle..."
git add Day5_Staging_Security_Bundle.py .env.production
git commit -m 'Day 5: Staging & Security Bundle — BasicAuth, RateLimit, SecureHeaders, Metrics'
git push origin main

# 4️⃣ Trigger Render deploy
echo "🌐 Triggering Render deployment..."
DEPLOY_HOOK="https://api.render.com/deploy/srv-d4a6l07gi27c739spc0g?key=ZBnxoh-Us8o"
curl -s -X POST "$DEPLOY_HOOK" > /tmp/deploy_response.json

# 5️⃣ Parse response
if grep -q '"deploy"' /tmp/deploy_response.json; then
  DEPLOY_ID=$(jq -r '.deploy.id' /tmp/deploy_response.json)
  echo "✅ Deploy triggered successfully (ID: $DEPLOY_ID)"
else
  echo "⚠️  Deploy trigger may have failed. Response:"
  cat /tmp/deploy_response.json
fi

# 6️⃣ Log action
mkdir -p logs
echo "$(date '+%Y-%m-%d %H:%M:%S') — Day 5 Deploy Triggered" >> logs/deploy_status.log

echo "✅ All done! Visit: https://the13th.onrender.com/healthz"
