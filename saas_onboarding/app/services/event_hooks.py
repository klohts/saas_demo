import os
import logging
from datetime import datetime, timezone
import aiohttp

logger = logging.getLogger("event_hooks")

THE13TH_URL = os.getenv("THE13TH_URL", "https://the13th.onrender.com/api/events")
THE13TH_API_KEY = os.getenv("THE13TH_API_KEY", "demo-key")


async def post_event(action: str, user: str, plan: str = None, source: str = "ai_automation") -> None:
    """
    Send structured event data to THE13TH API asynchronously.
    """
    payload = {
        "source": source,
        "action": action,
        "user": user,
        "plan": plan,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {THE13TH_API_KEY}"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(THE13TH_URL, json=payload, headers=headers, timeout=10) as response:
                if response.status < 400:
                    logger.info(f"Event sent to THE13TH: {payload}")
                else:
                    logger.warning(f"THE13TH responded with {response.status}: {await response.text()}")
    except Exception as e:
        logger.error(f"Failed to post event to THE13TH: {e}")
