import os, json, requests
from datetime import datetime
from pathlib import Path

LOG_PATH = Path("logs/admin_audit.log")
SLACK = os.getenv("SLACK_WEBHOOK_URL")
DISCORD = os.getenv("DISCORD_WEBHOOK_URL")
NOTIFY = os.getenv("AUDIT_NOTIFICATIONS", "true").lower() == "true"

def record_audit(event:str, actor:str="admin"):
    LOG_PATH.parent.mkdir(exist_ok=True)
    entry = {
        "ts": datetime.utcnow().isoformat(),
        "actor": actor,
        "event": event,
    }
    LOG_PATH.write_text(LOG_PATH.read_text() + json.dumps(entry) + "\n" if LOG_PATH.exists() else json.dumps(entry) + "\n")

    if NOTIFY:
        payload = {"text": f"🧠 THE13TH Audit Event: {actor} → {event}"}
        try:
            if SLACK:
                requests.post(SLACK, json=payload, timeout=4)
            if DISCORD:
                requests.post(DISCORD, json={"content": payload["text"]}, timeout=4)
        except Exception:
            pass
