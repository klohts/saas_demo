#!/bin/bash
# ============================================================
# 🚀 THE13TH Unified Deploy + Verify Script (v4.6.1)
# ------------------------------------------------------------
# Pushes code → triggers Render deploy → verifies live status.
# Author: Ken | Project: THE13TH | Date: $(date +'%Y-%m-%d')
# ============================================================

REPO_BRANCH="main"
DEPLOY_HOOK="https://api.render.com/deploy/srv-d475kper433s738vdmr0?key=AQ4JOubHX1g"
APP_URL="https://the13th.onrender.com"
ADMIN_KEY="${ADMIN_KEY:-the13th-admin}"

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🔄 Pushing latest changes to GitHub...${NC}"
git add .
git commit -m "Auto-deploy update on $(date '+%Y-%m-%d %H:%M:%S')" >/dev/null 2>&1
git push origin $REPO_BRANCH >/dev/null 2>&1

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✅ Code pushed successfully to GitHub ($REPO_BRANCH).${NC}"
else
  echo -e "${RED}❌ Git push failed. Please check your connection or repo.${NC}"
  exit 1
fi

echo -e "${YELLOW}🚀 Triggering deployment on Render...${NC}"
response=$(curl -s -X POST "$DEPLOY_HOOK")

if echo "$response" | grep -q '"deploy"'; then
  deploy_id=$(echo "$response" | grep -o '"id": *"[^"]*' | cut -d'"' -f4)
  echo -e "${GREEN}✅ Deployment started successfully!${NC}"
  echo -e "${BLUE}📦 Deployment ID:${NC} $deploy_id"
  echo -e "${YELLOW}🌍 App URL:${NC} $APP_URL"
else
  echo -e "${RED}❌ Deployment trigger failed!${NC}"
  echo "Response: $response"
  exit 1
fi

echo -e "${YELLOW}⏳ Waiting 30 seconds for Render to build...${NC}"
sleep 30

echo -e "${BLUE}🔎 Running live verification checks...${NC}\n"

# --- Check 1: Root ---
root_status=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL/")
if [ "$root_status" = "200" ]; then
  echo -e "${GREEN}✅ Root OK (${root_status})${NC}"
else
  echo -e "${RED}❌ Root failed (${root_status})${NC}"
fi

# --- Check 2: Plan listing ---
plan_json=$(curl -s "$APP_URL/api/plan")
if echo "$plan_json" | grep -q "Free"; then
  echo -e "${GREEN}✅ Plans endpoint OK${NC}"
else
  echo -e "${RED}❌ Plans endpoint failed${NC}"
  echo "$plan_json"
fi

# --- Check 3: Admin clients list ---
client_json=$(curl -s -H "X-ADMIN-KEY: $ADMIN_KEY" "$APP_URL/api/admin/clients")
if echo "$client_json" | grep -q "clients"; then
  echo -e "${GREEN}✅ Admin clients endpoint OK${NC}"
else
  echo -e "${RED}❌ Admin endpoint failed${NC}"
  echo "$client_json"
fi

echo -e "\n${BLUE}🧭 Deployment & Verification complete!${NC}"
echo -e "🌍 Visit ${YELLOW}$APP_URL${NC} or ${YELLOW}$APP_URL/docs${NC} for API docs."
