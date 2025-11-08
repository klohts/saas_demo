#!/bin/bash
# ============================================================
# 🔍 THE13TH Post-Deploy Verification Script (Stage 9 v4.8.0)
# ------------------------------------------------------------
# Verifies brand layer, API layer, and demo-mode activation.
# Author: Ken | Project: THE13TH | Date: $(date +'%Y-%m-%d')
# ============================================================

APP_URL="https://the13th.onrender.com"
ADMIN_KEY="${ADMIN_KEY:-the13th-admin}"

GREEN='\033[0;32m'; RED='\033[0;31m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo -e "${BLUE}🔎 Running THE13TH full verification (Stage 9)…${NC}\n"

# --- Landing page branding ---
echo -e "${YELLOW}→ Checking landing page (/) for brand markers…${NC}"
root_html=$(curl -s "$APP_URL/")
if echo "$root_html" | grep -qi "THE13TH" && echo "$root_html" | grep -qi "automation meets intuition"; then
  echo -e "${GREEN}✅ Landing page branding OK${NC}"
else
  echo -e "${RED}❌ Landing page missing brand markers${NC}"
fi

# --- Docs page branding ---
echo -e "${YELLOW}→ Checking docs page (/docs13) for brand markers…${NC}"
docs_html=$(curl -s "$APP_URL/docs13")
if echo "$docs_html" | grep -qi "THE13TH" && echo "$docs_html" | grep -qi "automation meets intuition"; then
  echo -e "${GREEN}✅ Docs page branding OK${NC}"
else
  echo -e "${RED}❌ Docs page branding missing${NC}"
fi

# --- Root HTTP status ---
echo -e "${YELLOW}→ Checking root endpoint HTTP status…${NC}"
root_status=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL/")
[ "$root_status" = "200" ] && echo -e "${GREEN}✅ Root OK (200)${NC}" || echo -e "${RED}❌ Root failed (${root_status})${NC}"

# --- /api/plan ---
echo -e "${YELLOW}→ Checking /api/plan…${NC}"
plan_json=$(curl -s "$APP_URL/api/plan")
if echo "$plan_json" | grep -q "Free"; then
  echo -e "${GREEN}✅ Plans endpoint OK${NC}"
else
  echo -e "${RED}❌ Plans endpoint failed${NC}"
  echo "$plan_json"
fi

# --- /api/admin/clients ---
echo -e "${YELLOW}→ Checking /api/admin/clients…${NC}"
client_json=$(curl -s -H "X-ADMIN-KEY: $ADMIN_KEY" "$APP_URL/api/admin/clients")
if echo "$client_json" | grep -q "clients"; then
  echo -e "${GREEN}✅ Admin clients endpoint OK${NC}"
else
  echo -e "${RED}❌ Admin endpoint failed${NC}"
  echo "$client_json"
fi

# --- Demo mode & hello test ---
echo -e "${YELLOW}→ Checking /api/hello for demo-mode activation…${NC}"
# Try reading local demo key if available
DEMO_KEY_FILE="$PROJECT_DIR/tmp_demo_api_key.txt"
if [ -f "$DEMO_KEY_FILE" ]; then
  DEMO_KEY=$(cat "$DEMO_KEY_FILE")
else
  DEMO_KEY=$(echo "$client_json" | grep -oE '"api_key": ?"[^"]+' | head -1 | cut -d'"' -f4)
fi

hello_json=$(curl -s -H "X-API-Key: $DEMO_KEY" "$APP_URL/api/hello")
if echo "$hello_json" | grep -q '"demo_mode": *true'; then
  echo -e "${GREEN}✅ Demo mode active (${DEMO_KEY:0:10}…)${NC}"
else
  echo -e "${RED}❌ Demo mode check failed${NC}"
  echo "$hello_json"
fi

echo -e "\n${BLUE}🧭 Verification complete!${NC}"
echo -e "Visit ${YELLOW}$APP_URL${NC} or ${YELLOW}$APP_URL/docs13${NC} for brand-layer validation."
