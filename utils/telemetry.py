# utils/telemetry.py
import logging, os, time, json
from datetime import datetime
from fastapi import Request
from statistics import mean

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def get_log_file() -> str:
    """Return today's log file path."""
    return os.path.join(LOG_DIR, f"app_{datetime.utcnow().strftime('%Y-%m-%d')}.log")

def setup_logger():
    """Configure rotating daily log file + console logging."""
    log_file = get_log_file()

    # Create a new logger instance manually (avoids duplication issues)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Remove any existing handlers (important for reloads)
    if logger.hasHandlers():
        logger.handlers.clear()

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))

    # Attach both
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logging.info(f"🧩 Logger initialized — writing to {log_file}")


def telemetry_middleware(app):
    """Attach FastAPI middleware that records request timing + status."""
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = round((time.time() - start_time) * 1000, 2)
        log_line = {
            "ts": datetime.utcnow().isoformat(),
            "ip": request.client.host,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration
        }
        logging.info(json.dumps(log_line))
        return response
    return app

def parse_today_metrics():
    """Compute total requests & average duration for today's log."""
    log_file = get_log_file()
    if not os.path.exists(log_file):
        return {"requests_today": 0, "avg_duration_ms": 0.0}

    durations = []
    with open(log_file) as f:
        for line in f:
            try:
                # Find JSON segment — flexible detection for any log style
                if "| INFO |" in line:
                    json_str = line.split("| INFO |", 1)[-1].strip()
                elif "INFO:root:" in line:
                    json_str = line.split("INFO:root:", 1)[-1].strip()
                elif "| INFO|" in line:
                    json_str = line.split("| INFO|", 1)[-1].strip()
                else:
                    continue

                data = json.loads(json_str)
                durations.append(float(data.get("duration_ms", 0)))
            except Exception:
                continue

    return {
        "requests_today": len(durations),
        "avg_duration_ms": round(mean(durations), 2) if durations else 0.0,
    }

