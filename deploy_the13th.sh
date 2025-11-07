#!/bin/bash
# =========================================================
# 🚀 THE13TH Render Auto-Deploy Script
# ---------------------------------------------------------
# Pushes latest code to GitHub, triggers Render deploy hook,
# and prints colored status messages for easy visibility.
# Author: Ken | Project: THE13TH | Updated: $(date +'%Y-%m-%d')
# =========================================================

# --- Configuration ---
REPO_BRANCH="main"
DEPLOY_HOOK="https://api.render.com/deploy/srv-d475kper433s738vdmr0?key=AQ4JOubHX1g"
APP_URL="https://the13th.onrender.com"

# --- Color codes ---
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- Step 1: Git push ---
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

# --- Step 2: Trigger Render deploy ---
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

# --- Step 3: Completion ---
echo -e "${GREEN}✨ All done! Your app will update live at:${NC} ${APP_URL}"
echo -e "${YELLOW}🕓 Check Render dashboard for real-time logs.${NC}"
