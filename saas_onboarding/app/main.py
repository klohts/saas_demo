"""
saas_onboarding/app/main.py
Production-ready FastAPI entrypoint for the Onboarding + Stripe layer.
"""

import os
import json
import logging
import asyncio
from typing import Optional

from fastapi import (
    FastAPI,
    Request,
    Form,
    Depends,
    HTTPException,
)
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
    JSONResponse,
    PlainTextResponse,
    FileResponse,
)
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Local imports
from .config import settings
from .db import init_db, get_session
from .models import User
from .auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from .services.stripe_service import create_checkout_session, construct_event
from .services.event_hooks import post_event
from .utils.env_reload import watch_env_file

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("saas_onboarding")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

watch_env_file()

# ---------------------------------------------------------------------------
# App Initialization
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ---------------------------------------------------------------------------
# React Frontend Static Serving
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
FRONTEND_DIST = os.path.join(BASE_DIR, "the13th", "frontend", "dist")

if os.path.isdir(os.path.join(FRONTEND_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")
    logger.info("✅ Mounted frontend /assets")
else:
    logger.warning("⚠️ No frontend assets folder found at %s", FRONTEND_DIST)

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# ---------------------------------------------------------------------------
# Rate Limiting + Security Middleware
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.DOMAIN] if settings.DOMAIN else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self' https://cdn.tailwindcss.com 'unsafe-inline' data:;"
    return response

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    await init_db()
    logger.info("Database initialized ✅")
    logger.info("Application startup complete")

# ---------------------------------------------------------------------------
# DB Session Dependency
# ---------------------------------------------------------------------------
async def get_db() -> AsyncSession:
    async for session in get_session():
        yield session

# ---------------------------------------------------------------------------
# App Pages
# ---------------------------------------------------------------------------
@app.get("/")
@limiter.limit("60/minute")
async def home(request: Request):
    return templates.TemplateResponse("base.html", {"request": request, "title": "AI Automation"})

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "app": settings.APP_NAME}

# ---- AUTH ----
@app.get("/signup", response_class=HTMLResponse)
async def get_signup(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def post_signup(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    plan: str = Form("starter"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.email == email)
    exists = await db.execute(stmt)
    if exists.scalar_one_or_none():
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Email already registered."})

    user = User(email=email, hashed_password=hash_password(password), plan=plan)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    request.session["pending_user_id"] = user.id

    checkout = await create_checkout_session(
        customer_email=email,
        plan=plan,
        success_url=f"{settings.DOMAIN}/signup/success",
        cancel_url=f"{settings.DOMAIN}/signup/cancel",
    )
    asyncio.create_task(post_event("signup", user=email, plan=plan))
    return RedirectResponse(checkout["url"], status_code=303)

@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def post_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

    token = create_access_token(subject=str(user.id))
    r = RedirectResponse("/dashboard", status_code=303)
    r.set_cookie("access_token", f"Bearer {token}", httponly=True)
    return r

@app.get("/dashboard")
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    cookie = request.cookies.get("access_token")
    if not cookie:
        return RedirectResponse("/login")

    uid = decode_access_token(cookie.split()[1])
    res = await db.execute(select(User).where(User.id == int(uid)))
    user = res.scalar_one_or_none()
    if not user:
        return RedirectResponse("/login")

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user_email": user.email,
        "plan": user.plan,
    })

# ---------------------------------------------------------------------------
# Stripe Webhook
# ---------------------------------------------------------------------------
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    event = construct_event(await request.body(), request.headers.get("stripe-signature"))
    asyncio.create_task(post_event("stripe_event", payload=event))
    return PlainTextResponse("ok")

# ---------------------------------------------------------------------------
# SPA Fallback (MUST BE LAST)
# ---------------------------------------------------------------------------
@app.get("/{path:path}", include_in_schema=False)
async def spa_fallback(path: str):
    # Prevent API hijack
    if path.startswith(("api", "docs", "openapi.json", "healthz")):
        raise HTTPException(status_code=404)

    index = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return {"status": "frontend_not_found"}
