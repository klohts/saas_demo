#!/bin/bash
set -e  # Exit on error

LOG_DIR=${LOG_DIR:-/opt/render/project/src/logs}
MAX_DAYS=7

# Webhook URLs (set these as Render environment variables)
SLACK_WEBHOOK="${SLACK_WEBHOOK_URL}"
DISCORD_WEBHOOK="${DISCORD_WEBHOOK_URL}"

mkdir -p "$LOG_DIR"

echo "🧹 Cleaning logs older than $MAX_DAYS days in $LOG_DIR"

if find "$LOG_DIR" -type f -mtime +"$MAX_DAYS" -delete; then
    echo "✅ Log cleanup succeeded"
else
    ERROR_MSG="❌ Log cleanup FAILED on $(date)"

    echo "$ERROR_MSG"

    # Send Slack Alert
    [[ -n "$SLACK_WEBHOOK" ]] && curl -X POST -H "Content-type: application/json" \
        --data "{\"text\":\"$ERROR_MSG\"}" "$SLACK_WEBHOOK"

    # Send Discord Alert
    [[ -n "$DISCORD_WEBHOOK" ]] && curl -X POST -H "Content-type: application/json" \
        --data "{\"content\":\"$ERROR_MSG\"}" "$DISCORD_WEBHOOK"

    exit 1
fi
