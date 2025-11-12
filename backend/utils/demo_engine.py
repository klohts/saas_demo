from __future__ import annotations
import threading, time, random, logging, os
from typing import Optional
from urllib.parse import urljoin
try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger("demo_engine")
DEFAULT_INTERVAL = int(os.getenv("DEMO_EVENT_INTERVAL", "10"))

try:
    from backend.core.analytics import get_engine
    HAS_ENGINE = True
except Exception:
    HAS_ENGINE = False

class DemoEngine:
    def __init__(self, interval:int=DEFAULT_INTERVAL, enabled:bool=True, base_url:str="http://127.0.0.1:8000"):
        self.interval = interval
        self.enabled = enabled
        self.base_url = base_url.rstrip("/")
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._engine = get_engine() if HAS_ENGINE else None

    def start(self):
        if not self.enabled:
            return
        if self._thread and self._thread.is_alive():
            return
        logger.info("DemoEngine starting")
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        users = ["alice","bob","carol","ken","sarah"]
        actions = ["login","view_dashboard","create_lead","upgrade_plan"]
        while not self._stop.is_set():
            u, a = random.choice(users), random.choice(actions)
            self.emit(u,a)
            time.sleep(max(1, self.interval + random.uniform(-self.interval*0.3,self.interval*0.3)))

    def emit(self,user:str,action:str):
        payload = {"user":user,"action":action}
        if self._engine and hasattr(self._engine,"record_event"):
            try:
                self._engine.record_event(user,action)
                return
            except Exception:
                pass
        if requests:
            try:
                url = urljoin(self.base_url + "/", "analytics/event")
                requests.post(url,json=payload,timeout=2)
            except Exception:
                logger.warning("DemoEngine: HTTP post failed")
