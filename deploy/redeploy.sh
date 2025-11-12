
#!/usr/bin/env bash
set -euo pipefail

if [ -z "${RENDER_DEPLOY_HOOK:-}" ]; then
  echo "ERROR: RENDER_DEPLOY_HOOK not set. Export it first."
  exit 2
fi

echo "Triggering Render deploy hook..."
curl -sS -X POST "$RENDER_DEPLOY_HOOK" -H "Content-Type: application/json" -d '{}' \
  && echo "Deploy triggered." || { echo "Failed to trigger deploy"; exit 3; }
