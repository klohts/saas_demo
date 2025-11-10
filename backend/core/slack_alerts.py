import os
import requests
from datetime import datetime

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def send_slack(text: str):
    if not SLACK_WEBHOOK_URL:
        return
    try:
        requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=5)
    except Exception as e:
        print("Slack error:", e)


# Spike detector (MVP version)
class SpikeDetector:
    def __init__(self, threshold=5):
        self.threshold = threshold
        self.counts = {}

    def hit(self, user: str, action: str):
        key = f"{user}:{action}"
        self.counts[key] = self.counts.get(key, 0) + 1
        n = self.counts[key]

        if n >= self.threshold:
            send_slack(
                f"🚨 *Spike Alert* — `{user}` performed `{action}` {n} times!\n"
                f"Time: {datetime.utcnow().isoformat()}Z"
            )
            self.counts[key] = 0  # reset to avoid spam
