# utils/telemetry.py
import logging, os, time
from datetime import datetime
from fastapi import Request

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def get_log_file() -> str:
    return os.path.join(LOG_DIR, f"app_{datetime.utcnow().strftime('%Y-%m-%d')}.log")

def setup_logger():
    log_file = get_log_file()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ],
    )

def telemetry_middleware(app):
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = round((time.time() - start_time) * 1000, 2)
        client_ip = request.client.host
        path = request.url.path
        method = request.method
        status = response.status_code

        logging.info(f"{client_ip} | {method} {path} | {status} | {duration} ms")
        return response
    return app
