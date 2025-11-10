import json
import os
from datetime import datetime
from typing import Dict

STORE_PATH = "analytics_store.json"


class AnalyticsEngine:
    def __init__(self):
        self.store = {
            "events": [],
            "scores": {},
            "trend": {},
            "users": {}
        }
        self._load()

    def _load(self):
        if os.path.exists(STORE_PATH):
            try:
                with open(STORE_PATH, "r") as f:
                    self.store = json.load(f)
            except:
                print("Failed to load analytics store, starting fresh")

    def _save(self):
        with open(STORE_PATH, "w") as f:
            json.dump(self.store, f, indent=2)

    def record_event(self, user: str, action: str):
        now = datetime.utcnow()
        day = now.strftime("%Y-%m-%d")

        event = {
            "user": user,
            "action": action,
            "ts": now.isoformat()
        }

        # Save event
        self.store["events"].append(event)

        # Score tally
        self.store["scores"][user] = self.store["scores"].get(user, 0) + 1

        # Daily trend
        self.store["trend"][day] = self.store["trend"].get(day, 0) + 1

        # Per-user tracking
        if user not in self.store["users"]:
            self.store["users"][user] = {
                "events": 0,
                "score": 0,
                "last_seen": None
            }

        self.store["users"][user]["events"] += 1
        self.store["users"][user]["score"] += 1
        self.store["users"][user]["last_seen"] = now.isoformat()

        self._save()
        return event

    def get_scores(self):
        return {
            "scores": self.store.get("scores", {}),
            "trend": self.store.get("trend", {})
        }

    def get_timeseries(self):
        return self.store.get("trend", {})

    def get_users(self):
        return self.store.get("users", {})


# Singleton engine
engine = AnalyticsEngine()

def get_engine():
    return engine
