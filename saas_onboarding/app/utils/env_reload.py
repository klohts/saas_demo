import os
import time
import threading
from dotenv import load_dotenv

def watch_env_file(interval: int = 3):
    """
    Automatically reload .env when it changes (dev use only).
    """
    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
        return

    last_mtime = os.path.getmtime(env_path)

    def _watch():
        nonlocal last_mtime
        while True:
            time.sleep(interval)
            try:
                mtime = os.path.getmtime(env_path)
                if mtime != last_mtime:
                    last_mtime = mtime
                    load_dotenv(override=True)
                    print("[DEV] .env reloaded.")
            except Exception:
                pass

    threading.Thread(target=_watch, daemon=True).start()
