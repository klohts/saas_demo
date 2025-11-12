# ============================================
# Day 5: Staging & Security Bundle — THE13TH
# ============================================
# Location: ~/AIAutomationProjects/saas_demo/the13th/Day5_Staging_Security_Bundle.py

import os
import logging
import secrets
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic_settings import BaseSettings
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# ============================================
# Configuration
# ============================================
class Settings(BaseSettings):
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    ADMIN_USER: str = os.getenv("ADMIN_USER", "admin")
    ADMIN_PASS: str = os.getenv("ADMIN_PASS", "password")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")

    model_config = {
        "extra": "ignore",
        "env_file": ".env.production" if os.path.exists(".env.production") else ".env",
    }

settings = Settings()

# ============================================
# Logging
# ============================================
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "app.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("THE13TH")
logger.info(f"Starting THE13TH in {settings.ENVIRONMENT} mode")

# ============================================
# Security Headers Middleware
# ============================================
class SecureHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

# ============================================
# Basic Auth
# ============================================
security = HTTPBasic()

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, settings.ADMIN_USER)
    correct_password = secrets.compare_digest(credentials.password, settings.ADMIN_PASS)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True

# ============================================
# Rate Limiter Setup
# ============================================
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="THE13TH — Secure Staging", version="1.0.0")
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(
    RateLimitExceeded,
    lambda request, exc: JSONResponse(
        status_code=429, content={"error": "Rate limit exceeded. Try again later."}
    ),
)

# ============================================
# Global Middleware
# ============================================
app.add_middleware(SecureHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# Routes
# ============================================
@app.get("/healthz")
def healthz():
    return {"status": "ok", "app": "THE13TH", "env": settings.ENVIRONMENT}

@app.get("/metrics")
def metrics():
    return {"requests": "tracked", "rate_limit": "100/min", "env": settings.ENVIRONMENT}

@app.get("/admin/dashboard", dependencies=[Depends(verify_admin)])
@limiter.limit("10/minute")
async def admin_dashboard(request: Request):
    return {"status": "authenticated", "message": "Welcome to THE13TH Admin"}

@app.get("/")
@limiter.limit("50/minute")
async def root(request: Request):
    return {
        "message": "Welcome to THE13TH Secure Deployment",
        "env": settings.ENVIRONMENT,
    }


# ============================================
# Entrypoint
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("Day5_Staging_Security_Bundle:app", host="0.0.0.0", port=8000, reload=True)
