#!/bin/bash
# ============================================================
# 🔍 THE13TH Post-Deploy Verification Script
# ------------------------------------------------------------
# Checks API health & client module status after Render deploy.
# Author: Ken | Project: THE13TH | Date: $(date +'%Y-%m-%d')
# ============================================================

APP_URL="https://the13th.onrender.com"
ADMIN_KEY="${ADMIN_KEY:-the13th-admin}"

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🔎 Running THE13TH post-deploy checks...${NC}\n"

# --- Check 1: App root ---
echo -e "${YELLOW}→ Checking root endpoint (/)...${NC}"
root_status=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL/")
if [ "$root_status" = "200" ]; then
  echo -e "${GREEN}✅ Root OK (${root_status})${NC}"
else
  echo -e "${RED}❌ Root failed (${root_status})${NC}"
fi

# --- Check 2: Plan listing ---
echo -e "${YELLOW}→ Checking /api/plan...${NC}"
plan_json=$(curl -s "$APP_URL/api/plan")
if echo "$plan_json" | grep -q "Free"; then
  echo -e "${GREEN}✅ Plans endpoint OK${NC}"
else
  echo -e "${RED}❌ Plans endpoint failed${NC}"
  echo "$plan_json"
fi

# --- Check 3: Admin clients list ---
echo -e "${YELLOW}→ Checking /api/admin/clients...${NC}"
client_json=$(curl -s -H "X-ADMIN-KEY: $ADMIN_KEY" "$APP_URL/api/admin/clients")
if echo "$client_json" | grep -q "clients"; then
  echo -e "${GREEN}✅ Admin clients endpoint OK${NC}"
else
  echo -e "${RED}❌ Admin endpoint failed${NC}"
  echo "$client_json"
fi

# --- Final summary ---
echo -e "\n${BLUE}🧭 Verification complete!${NC}"
echo -e "Visit ${YELLOW}$APP_URL${NC} or ${YELLOW}$APP_URL/docs${NC} for API docs."
