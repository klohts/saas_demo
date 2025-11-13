#!/usr/bin/env bash
# ============================================================
# Day 9 — Render Docker Stability Fix Bundle
# Location: ~/AIAutomationProjects/saas_demo/the13th/fix_day9_docker_stability.sh
# Purpose:
#   • Remove render.yaml to prevent infinite redeploy loops
#   • Apply a clean, stable Dockerfile for THE13TH
#   • Apply a proper .dockerignore
#   • Trigger a safe redeploy
# ============================================================

set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$ROOT_DIR/.." && pwd)"
DOCKERFILE_PATH="$ROOT_DIR/Dockerfile"
DOCKERIGNORE_PATH="$ROOT_DIR/.dockerignore"
RENDER_YAML="$REPO_DIR/render.yaml"

# -------------------------
# 1. Remove render.yaml
# -------------------------
echo "🔁 Removing render.yaml (prevents auto-IaC redeploy loops)..."
if [[ -f "$RENDER_YAML" ]]; then
  rm -f "$RENDER_YAML"
  echo "✔ Removed: $RENDER_YAML"
else
  echo "✔ Already removed"
fi

# -------------------------
# 2. Write stable Dockerfile
# -------------------------
echo "🔁 Writing stable Dockerfile..."
cat > "$DOCKERFILE_PATH" << 'EOF'
# ============================================================
# THE13TH — Stable Production Dockerfile (Day 9 Fix)
# ============================================================
# Frontend build stage
FROM node:18 AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps
COPY frontend .
RUN npm run build

# Backend stage
FROM python:3.10-slim AS backend
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy backend app code
COPY app ./app
COPY config ./config
COPY data ./data
COPY static ./static
COPY templates ./templates

# Copy built SPA
COPY --from=frontend /app/frontend/dist /app/frontend/dist

ENV PORT=8000
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

echo "✔ Dockerfile updated: $DOCKERFILE_PATH"

# -------------------------
# 3. Write .dockerignore
# -------------------------
echo "🔁 Writing .dockerignore..."
cat > "$DOCKERIGNORE_PATH" << 'EOF'
# Ignore venvs
.venv/
the13th/.venv/

# Ignore logs
logs/*

# Ignore local databases
*.db
**/*.db

# Ignore git
.git/
.gitignore

# Ignore caches
__pycache__/
**/__pycache__/

# Ignore Node
node_modules/
frontend/node_modules/
EOF

echo "✔ .dockerignore updated: $DOCKERIGNORE_PATH"

# -------------------------
# 4. Git commit
# -------------------------
echo "🔁 Committing changes..."
cd "$REPO_DIR"

git add the13th/Dockerfile the13th/.dockerignore || true
if [[ -f "$RENDER_YAML" ]]; then git rm -f "$RENDER_YAML"; fi

git commit -m "fix(day9): stable Dockerfile + remove render.yaml + .dockerignore" || true

echo "✔ Git commit complete"

# -------------------------
# 5. Optional: trigger Render deploy
# -------------------------
if [[ -n "${RENDER_DEPLOY_HOOK:-}" ]]; then
  echo "🚀 Triggering Render deploy via hook…"
  curl -s -X POST "$RENDER_DEPLOY_HOOK"
  echo
  echo "✔ Deploy triggered"
else
  echo "⚠️ RENDER_DEPLOY_HOOK not set — skipping auto-deploy"
fi

# -------------------------
# Done
# -------------------------
echo "🎯 Day 9 Docker stability fix applied successfully."
