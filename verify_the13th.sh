#!/bin/bash
# ============================================================
# 🔍 THE13TH Post-Deploy Verification Script (Stage 8)
# ------------------------------------------------------------
# Verifies API + Branding endpoints after Render deploy.
# Author: Ken | Project: THE13TH | Date: $(date +'%Y-%m-%d')
# ============================================================

APP_URL="https://the13th.onrender.com"
ADMIN_KEY="${ADMIN_KEY:-the13th-admin}"

#!/bin/bash
source .env 2>/dev/null

API_KEY=$THE13TH_API_KEY


GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🔎 Running THE13TH full verification (Stage 8)...${NC}\n"

# --- Root page check ---
echo -e "${YELLOW}→ Checking landing page (/) for brand markers...${NC}"
root_html=$(curl -s "$APP_URL/")
if echo "$root_html" | grep -qi "THE13TH" && echo "$root_html" | grep -qi "automation meets intuition"; then
  echo -e "${GREEN}✅ Landing page branding OK${NC}"
else
  echo -e "${RED}❌ Landing page missing brand markers${NC}"
  echo "$root_html" | head -n 10
fi

# --- Docs page check ---
echo -e "${YELLOW}→ Checking docs page (/docs13) for brand markers...${NC}"
docs_html=$(curl -s "$APP_URL/docs13")
if echo "$docs_html" | grep -qi "THE13TH" && echo "$docs_html" | grep -qi "automation meets intuition"; then
  echo -e "${GREEN}✅ Docs page branding OK${NC}"
else
  echo -e "${RED}❌ Docs page branding missing or incorrect${NC}"
  echo "$docs_html" | head -n 10
fi

# --- Root HTTP status ---
echo -e "${YELLOW}→ Checking root endpoint HTTP status...${NC}"
root_status=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL/")
if [ "$root_status" = "200" ]; then
  echo -e "${GREEN}✅ Root OK (${root_status})${NC}"
else
  echo -e "${RED}❌ Root failed (${root_status})${NC}"
fi

# --- /api/plan ---
echo -e "${YELLOW}→ Checking /api/plan...${NC}"
plan_json=$(curl -s "$APP_URL/api/plan")
if echo "$plan_json" | grep -q "Free"; then
  echo -e "${GREEN}✅ Plans endpoint OK${NC}"
else
  echo -e "${RED}❌ Plans endpoint failed${NC}"
  echo "$plan_json"
fi

# --- /api/admin/clients ---
echo "→ Checking /api/admin/clients..."
RESP=$(curl -s https://the13th.onrender.com/api/admin/clients \
  -H "X-API-Key: $API_KEY")

if [[ $RESP == *"Invalid API Key"* || $RESP == *"required"* ]]; then
  echo "❌ Admin endpoint failed auth"
  echo "$RESP"
else
  echo "✅ Admin endpoint OK"
fi


# --- Summary ---
echo -e "\n${BLUE}🧭 Verification complete!${NC}"
echo -e "Visit ${YELLOW}$APP_URL${NC} or ${YELLOW}$APP_URL/docs13${NC} for brand-layer validation."
