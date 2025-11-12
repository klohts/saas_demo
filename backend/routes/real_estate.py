from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any
from pathlib import Path
import os, logging, json, time
from datetime import datetime

# Tries to reuse existing analytics engine if present
try:
    from backend.core.analytics import get_engine
    engine = get_engine()
except Exception:
    engine = None

router = APIRouter()

# Event schema
class REEvent(BaseModel):
    user: str
    action: str
    property_id: str | None = None
    metadata: Dict[str, Any] | None = None
    ts: float | None = None

ZAPIER_WEBHOOK = os.getenv("ZAPIER_WEBHOOK_URL", "")
AI_ENGINE_URL = os.getenv("AI_ENGINE_URL", "")

def send_to_zapier(payload: dict) -> bool:
    """Send event to Zapier webhook if configured. Non-blocking best-effort."""
    if not ZAPIER_WEBHOOK:
        logging.debug("ZAP not configured")
        return False
    try:
        import requests
        r = requests.post(ZAPIER_WEBHOOK, json=payload, timeout=5)
        logging.info(f"Zapier forwarded: {{r.status_code}} for {{payload.get('action')}}")
        return r.ok
    except Exception as e:
        logging.exception("Failed sending to Zapier: %s", e)
        return False

def notify_ai_lead_engine(payload: dict) -> bool:
    """Optional: send lightweight payload to AI lead reply engine."""
    if not AI_ENGINE_URL:
        return False
    try:
        import requests
        r = requests.post(AI_ENGINE_URL, json=payload, timeout=5)
        logging.info(f"AI engine forwarded: {{r.status_code}} for {{payload.get('action')}}")
        return r.ok
    except Exception as e:
        logging.exception("Failed sending to AI engine: %s", e)
        return False

# Record event and optionally route to Zapier/AI
@router.post("/event")
async def record_event(e: REEvent):
    payload = e.dict()
    payload['ts'] = payload.get('ts') or time.time()
    # prefer analytics engine if present
    try:
        if engine:
            rec = engine.record_event(payload.get('user','unknown'), payload.get('action'), payload)
        else:
            # fallback: append to backend/data/events.json if exists
            data_file = Path(__file__).resolve().parents[2] / 'data' / 'events.json'
            if data_file.exists():
                try:
                    obj = json.loads(data_file.read_text() or "{{}}")
                except Exception:
                    obj = {{}}
            else:
                obj = {{}}
            # simple list per user
            obj.setdefault(payload.get('user','unknown'), []).append(payload)
            data_file.parent.mkdir(parents=True, exist_ok=True)
            data_file.write_text(json.dumps(obj, indent=2))
            rec = payload
    except Exception as ex:
        logging.exception("record_event failed: %s", ex)
        raise HTTPException(status_code=500, detail="record failed")

    # Forward to Zapier & AI (best-effort, non-blocking)
    try:
        send_to_zapier(payload)
    except Exception:
        pass
    try:
        notify_ai_lead_engine(payload)
    except Exception:
        pass

    # Return simple ack
    return {{ "status": "ok", "event": payload }}

# Summary endpoint - domain-focused for Real Estate
@router.get("/summary")
def summary():
    """Return simple real-estate KPIs for demo:
    - top_listings: {{property_id: views}}
    - leads_by_agent: {{agent: leads}}
    - weekly_leads: {{date: count}}
    """
    try:
        if engine:
            # use engine.get_events() if available, else use engine.time series helpers
            events = []
            try:
                events = engine.get_events()
            except Exception:
                # engine may not expose get_events; fallback to engine.events store
                events = getattr(engine, 'events', []) or []
        else:
            data_file = Path(__file__).resolve().parents[2] / 'data' / 'events.json'
            if data_file.exists():
                raw = json.loads(data_file.read_text() or '{{}}')
                events = []
                for user, evs in raw.items():
                    for e in evs:
                        e['_user'] = user
                        events.append(e)
            else:
                events = []

        # compute simple KPIs
        top_listings: dict = {{}}
        leads_by_agent: dict = {{}}
        weekly_leads: dict = {{}}
        now = datetime.utcnow()

        for e in events:
            action = e.get('action')
            pid = e.get('property_id')
            user = e.get('user') or e.get('_user') or 'unknown'
            ts = e.get('ts') or e.get('timestamp') or None
            if ts:
                try:
                    created = datetime.utcfromtimestamp(float(ts))
                except Exception:
                    try:
                        created = datetime.fromisoformat(str(ts))
                    except Exception:
                        created = now
            else:
                created = now

            day = created.strftime('%Y-%m-%d')
            # interpret some actions
            if action == 'property_viewed' and pid:
                top_listings[pid] = top_listings.get(pid, 0) + 1
            if action in ('lead_generated', 'contacted_agent'):
                leads_by_agent[user] = leads_by_agent.get(user, 0) + 1
                weekly_leads[day] = weekly_leads.get(day, 0) + 1

        # top listings sorted
        top_listings_sorted = dict(sorted(top_listings.items(), key=lambda x: x[1], reverse=True)[:10])

        return {{
            'top_listings': top_listings_sorted,
            'leads_by_agent': leads_by_agent,
            'weekly_leads': weekly_leads,
            'raw_count': len(events)
        }}
    except Exception as ex:
        logging.exception("summary failed: %s", ex)
        raise HTTPException(status_code=500, detail='calc failed')
