import os, requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api import routes_gmail_demo
from app.core.auth_guard import verify_api_key
from app.services.gmail_service import get_gmail_service

app = FastAPI(title="AI Email SaaS", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def api_guard(request: Request, call_next):
    if request.url.path not in ("/", "/health", "/openapi.json", "/docs"):
        try:
            await verify_api_key(request)
        except Exception as e:
            if hasattr(e, "status_code"):
                return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)

def notify_slack(msg: str):
    webhook = os.getenv("SLACK_WEBHOOK")
    if webhook:
        try: requests.post(webhook, json={"text": msg})
        except Exception: pass

@app.on_event("startup")
def startup_check():
    print("\n🔍 Startup Check")
    required = ["APP_API_KEY", "GEMINI_API_KEY", "EMAIL_SENDER_OVERRIDE", "GMAIL_OAUTH_CLIENT_JSON"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"⚠️ Missing env vars: {', '.join(missing)}"); notify_slack(f"⚠️ Missing env vars: {', '.join(missing)}")
    else:
        print("✅ Critical env loaded.")

    try:
        get_gmail_service()
        print("✅ Gmail token valid (OAuth2).")
    except Exception as e:
        print(f"⚠️ Gmail not authorized yet: {e}")

    print("--------------------------------------------------\n")
    notify_slack("🚀 AI Email SaaS started.")

@app.get("/")
def root(): return {"status": "ok", "message": "AI Email SaaS API online"}

@app.get("/health")
def health(): return {"status": "ok", "message": "Server healthy and running"}

app.include_router(routes_gmail_demo.router)
