#!/usr/bin/env python3
"""
create_analytics_engine.py

Creates:
 - backend/core/analytics.py    (Analytics engine)
 - backend/routes/analytics.py  (FastAPI router for analytics)
 - backend/data/events.json     (sample events store if not present)
Patches main.py (searches for backend/main.py, then ./main.py) to include the analytics router.
Backs up any main.py it modifies to main.py.bak.timestamp
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
import re
import sys

ROOT = Path.cwd()
BACKEND = ROOT / "backend"
CORE_DIR = BACKEND / "core"
ROUTES_DIR = BACKEND / "routes"
DATA_DIR = BACKEND / "data"

MAIN_CANDIDATES = [BACKEND / "main.py", ROOT / "main.py"]

def ensure_dirs():
    for d in (CORE_DIR, ROUTES_DIR, DATA_DIR):
        d.mkdir(parents=True, exist_ok=True)

def write_file(path: Path, content: str, force=False):
    if path.exists() and not force:
        # do not overwrite if identical
        existing = path.read_text()
        if existing == content:
            print(f"[unchanged] {path}")
            return
        else:
            print(f"[overwrite] {path} (existing file differs)")
    path.write_text(content)
    print(f"[written] {path}")

def create_sample_events():
    sample = [
        {
            "id": "evt_001",
            "client": "bob",
            "action": "client_upgrade",
            "value": 199,
            "timestamp": (datetime.utcnow()).isoformat() + "Z"
        },
        {
            "id": "evt_002",
            "client": "alice",
            "action": "rule_trigger",
            "rule": "lead_followup",
            "timestamp": (datetime.utcnow()).isoformat() + "Z"
        },
        {
            "id": "evt_003",
            "client": "bob",
            "action": "login",
            "timestamp": (datetime.utcnow()).isoformat() + "Z"
        },
        {
            "id": "evt_004",
            "client": "team_x",
            "action": "alert_raised",
            "severity": "high",
            "timestamp": (datetime.utcnow()).isoformat() + "Z"
        }
    ]
    path = DATA_DIR / "events.json"
    if not path.exists():
        path.write_text(json.dumps(sample, indent=2))
        print(f"[created] sample events store at {path}")
    else:
        print(f"[exists] events store at {path} (not overwritten)")

def analytics_core_content():
    return '''"""
backend/core/analytics.py

Lightweight Analytics Engine:
 - Loads events from a JSON file (backend/data/events.json)
 - Normalizes events
 - Computes a simple activity score per client
 - Computes simple trend and anomaly signals

This is intentionally self-contained and easy to reason about.
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

EVENTS_PATH = Path(__file__).parents[1] / "data" / "events.json"

class AnalyticsEngine:
    def __init__(self, events_path: Optional[Path] = None):
        self.events_path = Path(events_path) if events_path else EVENTS_PATH
        self._events = []  # raw events
        self._by_client = defaultdict(list)
        self.reload_events()

    def reload_events(self):
        try:
            text = self.events_path.read_text()
            data = json.loads(text) if text.strip() else []
        except Exception:
            data = []
        self._events = [self._normalize(e) for e in data]
        self._by_client = defaultdict(list)
        for e in self._events:
            self._by_client[e['client']].append(e)

    def _normalize(self, ev: Dict[str, Any]) -> Dict[str, Any]:
        # Ensure fields and typed timestamp
        e = dict(ev)
        if 'timestamp' in e:
            try:
                e['_ts'] = datetime.fromisoformat(e['timestamp'].replace("Z", "+00:00"))
            except Exception:
                e['_ts'] = datetime.utcnow()
        else:
            e['_ts'] = datetime.utcnow()
        e.setdefault('action', 'unknown')
        e.setdefault('client', 'unknown')
        return e

    def add_event(self, ev: Dict[str, Any], persist: bool = True):
        e = dict(ev)
        if 'timestamp' not in e:
            e['timestamp'] = datetime.utcnow().isoformat() + "Z"
        # append to file if persist True
        if persist:
            try:
                data = []
                if self.events_path.exists():
                    data = json.loads(self.events_path.read_text())
                data.append(e)
                self.events_path.write_text(json.dumps(data, indent=2))
            except Exception:
                pass
        # reload cache
        self.reload_events()
        return e

    def clients(self) -> List[str]:
        return list(self._by_client.keys())

    def client_events(self, client: str, limit: int = 100) -> List[Dict[str, Any]]:
        evs = sorted(self._by_client.get(client, []), key=lambda x: x['_ts'], reverse=True)
        return evs[:limit]

    def _score_event(self, event: Dict[str, Any]) -> int:
        # simple heuristic scoring: points per action type
        base = {
            'client_upgrade': 50,
            'rule_trigger': 10,
            'alert_raised': 20,
            'login': 2,
            'unknown': 0,
        }
        return base.get(event.get('action'), 5)

    def score_client(self, client: str) -> Dict[str, Any]:
        evs = self._by_client.get(client, [])
        score = sum(self._score_event(e) for e in evs)
        # recency boost: events in last 7 days get +1% per event
        now = datetime.utcnow()
        recent_count = sum(1 for e in evs if (now - e['_ts']) <= timedelta(days=7))
        recency_boost = int((recent_count * 1))  # small boost
        return {
            'client': client,
            'score': score + recency_boost,
            'events_count': len(evs),
            'recent_count': recent_count
        }

    def compute_all_scores(self) -> List[Dict[str, Any]]:
        results = []
        for client in self.clients():
            results.append(self.score_client(client))
        # sort descending by score
        results.sort(key=lambda x: x['score'], reverse=True)
        return results

    def global_trend(self) -> Dict[str, Any]:
        # very simple trend: compare number of events last 7 days vs previous 7 days
        now = datetime.utcnow()
        last7 = 0
        prev7 = 0
        for e in self._events:
            d = e['_ts']
            delta = (now - d).days
            if delta < 7:
                last7 += 1
            elif 7 <= delta < 14:
                prev7 += 1
        pct = None
        if prev7 == 0:
            pct = (last7 * 100) if last7 > 0 else 0
        else:
            pct = int(((last7 - prev7) / max(prev7,1)) * 100)
        return {'last7': last7, 'prev7': prev7, 'pct_change': pct}

    def detect_anomalies(self) -> List[Dict[str, Any]]:
        # flag clients with sudden jumps >100% in last 7 days vs prev 7
        anomalies = []
        now = datetime.utcnow()
        for client, evs in self._by_client.items():
            last7 = sum(1 for e in evs if (now - e['_ts']).days < 7)
            prev7 = sum(1 for e in evs if 7 <= (now - e['_ts']).days < 14)
            if prev7 == 0 and last7 >= 5:
                anomalies.append({'client': client, 'reason': 'spike_new', 'last7': last7, 'prev7': prev7})
            elif prev7 > 0 and last7 > prev7 * 2:
                anomalies.append({'client': client, 'reason': 'spike', 'last7': last7, 'prev7': prev7})
        return anomalies

# Simple singleton engine for the app to import
_engine = None

def get_engine(reload: bool = False) -> AnalyticsEngine:
    global _engine
    if _engine is None or reload:
        _engine = AnalyticsEngine()
    return _engine
'''

def routes_content():
    return '''"""
backend/routes/analytics.py

FastAPI routes exposing analytics summaries:
 - GET /analytics/scores
 - GET /analytics/global
 - GET /analytics/clients/{client}/history
 - POST /analytics/events  (accepts JSON event to append)
"""

from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any
from ..core.analytics import get_engine
from datetime import datetime

router = APIRouter()
engine = get_engine()

@router.get("/scores")
def scores():
    """
    Returns all clients' scores and a simple global trend summary.
    """
    engine.reload_events()
    data = engine.compute_all_scores()
    global_trend = engine.global_trend()
    anomalies = engine.detect_anomalies()
    return {"clients": data, "global_trend": global_trend, "anomalies": anomalies}

@router.get("/global")
def global_summary():
    engine.reload_events()
    return engine.global_trend()

@router.get("/clients/{client}/history")
def client_history(client: str, limit: int = 100):
    engine.reload_events()
    evs = engine.client_events(client, limit=limit)
    # serialize timestamps
    out = []
    for e in evs:
        copy = dict(e)
        if '_ts' in copy:
            copy['timestamp_iso'] = copy['_ts'].isoformat()
            del copy['_ts']
        out.append(copy)
    if not out:
        raise HTTPException(status_code=404, detail="client not found or no events")
    return {"client": client, "events": out}

@router.post("/events")
async def create_event(request: Request):
    """
    Accepts a JSON event and appends it to the events store.
    Expected JSON fields: client (str), action (str), timestamp (optional ISO str), any additional metadata.
    """
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="expected JSON object")
    if 'client' not in payload or 'action' not in payload:
        raise HTTPException(status_code=400, detail="must include 'client' and 'action'")
    # attach server timestamp if missing
    if 'timestamp' not in payload:
        payload['timestamp'] = datetime.utcnow().isoformat() + "Z"
    e = engine.add_event(payload, persist=True)
    return {"status": "ok", "event": e}
'''

def patch_main(main_path: Path):
    text = main_path.read_text()
    backup = main_path.with_suffix(main_path.suffix + f".bak.{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}")
    shutil.copy2(main_path, backup)
    print(f"[backup] {main_path} -> {backup}")

    # ensure import of router: try to import "from backend.routes.analytics import router as analytics_router"
    import_line = "from backend.routes.analytics import router as analytics_router"
    include_line = "app.include_router(analytics_router, prefix=\"/analytics\")"
    alt_import = "from routes.analytics import router as analytics_router"

    if import_line not in text and alt_import not in text:
        # insert import near top (after other imports) - place after first FastAPI import if exists
        inserted = False
        lines = text.splitlines()
        for idx, ln in enumerate(lines):
            if re.search(r"from fastapi import", ln) or re.search(r"import FastAPI", ln):
                # insert after this line
                lines.insert(idx+1, import_line)
                inserted = True
                break
        if not inserted:
            # fallback put near top
            lines.insert(0, import_line)
        text = "\\n".join(lines)
        print(f"[patched] inserted import into {main_path}")

    if include_line not in text:
        # find the app declaration
        # pattern: app = FastAPI(...
        m = re.search(r"(app\s*=\s*FastAPI\([\\s\\S]*?\\))", text, re.M)
        if m:
            # place include line after the app declaration block
            # find end of that line and insert after
            idx = text.find(m.group(0)) + len(m.group(0))
            text = text[:idx] + "\\n\\n" + include_line + text[idx:]
            print(f"[patched] inserted include_router after app declaration in {main_path}")
        else:
            # fallback: append at end
            text = text + "\\n\\n" + include_line + "\\n"
            print(f"[patched] appended include_router at end of {main_path}")

    main_path.write_text(text)
    print(f"[patched] {main_path} updated")

def main():
    ensure_dirs()
    write_file(CORE_DIR / "analytics.py", analytics_core_content())
    write_file(ROUTES_DIR / "analytics.py", routes_content())
    create_sample_events()

    # attempt to patch a main.py candidate
    patched = False
    for p in MAIN_CANDIDATES:
        if p.exists():
            try:
                patch_main(p)
                patched = True
                break
            except Exception as e:
                print(f"[error] failed to patch {p}: {e}")
    if not patched:
        print("[warn] No main.py found to patch. Please add the router import and include manually:")
        print("  from backend.routes.analytics import router as analytics_router")
        print("  app.include_router(analytics_router, prefix=\"/analytics\")")
    print("\\nDone. Next steps:")
    print(" - Start your FastAPI app (e.g. uvicorn backend.main:app --reload) or however you run it.")
    print(" - Visit GET /analytics/scores to see computed scores.")
    print(" - POST /analytics/events to add events for testing.")

if __name__ == '__main__':
    main()
