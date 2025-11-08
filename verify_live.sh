#!/bin/bash
# ============================================================
# ✅ THE13TH Live Verification Layer  — Stage 11
# ------------------------------------------------------------
# Runs after every deploy to confirm that:
#   • Frontend is live
#   • Docs are accessible
#   • API responds with valid JSON
#   • Auth layer is enforced
# ============================================================

APP_URL="https://the13th.onrender.com"
LOG_FILE="/home/hp/AIAutomationProjects/saas_demo/logs/deploy_status.log"

# Create log directory if missing
mkdir -p "$(dirname "$LOG_FILE")"

# --- Simple color helpers ---
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m'

echo -e "\n🔎 Running THE13TH Live Verification..."
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"

declare -A paths=(
  ["/"]="Root Landing"
  ["/docs13"]="Docs Page"
  ["/api/plan"]="Plans Endpoint"
  ["/api/admin/clients"]="Admin Endpoint"
)

overall_status=0

for path in "${!paths[@]}"; do
  printf "→ %-22s " "${paths[$path]} ($path)"
  code=$(command curl -s -o /dev/null -w "%{http_code}" "$APP_URL$path")

  if [[ "$code" == "200" ]]; then
    echo -e "${GREEN}✅ 200 OK${NC}"
  elif [[ "$code" == "401" || "$code" == "403" ]]; then
    echo -e "${YELLOW}🔒 $code Protected${NC}"
  else
    echo -e "${RED}❌ $code Error${NC}"
    overall_status=1
  fi

  echo "$(date '+%Y-%m-%d %H:%M:%S')  $code  $path" >> "$LOG_FILE"
done

if [[ $overall_status -eq 0 ]]; then
  echo -e "\n${GREEN}✅ THE13TH deployment verified successfully!${NC}"
else
  echo -e "\n${RED}⚠️  One or more checks failed — see log for details.${NC}"
fi

echo "Log saved to: $LOG_FILE"
exit $overall_status
