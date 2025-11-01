#!/usr/bin/env python3
import os, textwrap

ROOT = os.getcwd()

def write_file(path, content):
    """Create directories if needed and write a file."""
    dir_path = os.path.dirname(path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content).strip() + "\n")
    print(f"✅ {path} written.")

print("\n🚀 Finalizing AI Email SaaS production setup...\n")

# 1) app/core/config.py
write_file("app/core/config.py", """
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    app_env: str = "production"
    app_api_key: str | None = None
    x_api_key: str | None = None
    secret_key: str | None = None
    debug: bool = False
    base_url: str | None = None
    allowed_origins: str | None = None
    ai_provider: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    openai_api_key: str | None = None
    gmail_oauth_client_json: str | None = None
    email_sender_override: str | None = None
    database_url: str | None = None
    render_api_key: str | None = None
    render_service_id: str | None = None
    slack_webhook: str | None = None
    app_url: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

settings = Settings()
""")

# 2) app/core/auth_guard.py
write_file("app/core/auth_guard.py", """
from fastapi import Request, HTTPException, status
from dotenv import load_dotenv
import os

load_dotenv()

def _active_key() -> str | None:
    return os.getenv("X_API_KEY") or os.getenv("APP_API_KEY")

async def verify_api_key(request: Request):
    key = _active_key()
    if not key:
        raise HTTPException(status_code=500, detail="Server missing API key configuration")

    header_key = request.headers.get("X-API-Key")
    query_key = request.query_params.get("api_key")

    if header_key == key or query_key == key:
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing X-API-Key")
""")

# 3) app/services/gmail_service.py (OAuth2 for personal Gmail)
write_file("app/services/gmail_service.py", """
import os, base64, logging
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger("gmail_service")
logger.setLevel(logging.INFO)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
]

def get_gmail_service():
    creds = None
    token_path = os.getenv("GMAIL_TOKEN_PATH", "token.json")
    oauth_client_file = os.getenv("GMAIL_OAUTH_CLIENT_JSON", "gmail_oauth_client.json")

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(oauth_client_file):
                raise FileNotFoundError(f"OAuth client file not found: {oauth_client_file}")
            flow = InstalledAppFlow.from_client_secrets_file(oauth_client_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

def _create_message(to, subject, body_text, sender=None):
    msg = MIMEText(body_text)
    msg["to"] = to
    msg["subject"] = subject
    if sender:
        msg["from"] = sender
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw}

def send_email(service, to, subject, body_text, sender=None):
    try:
        body = _create_message(to, subject, body_text, sender)
        res = service.users().messages().send(userId="me", body=body).execute()
        return {"status": "ok", "id": res.get("id")}
    except HttpError as e:
        return {"status": "error", "error": str(e)}

def create_draft(service, to, subject, body_text, sender=None):
    try:
        body = _create_message(to, subject, body_text, sender)
        res = service.users().drafts().create(userId="me", body={"message": body}).execute()
        return {"status": "draft_created", "id": res.get("id")}
    except HttpError as e:
        return {"status": "error", "error": str(e)}

def draft_or_send_email(to, subject, body_text, dry_run=False):
    service = get_gmail_service()
    sender = os.getenv("EMAIL_SENDER_OVERRIDE")
    return create_draft(service, to, subject, body_text, sender) if dry_run \
        else send_email(service, to, subject, body_text, sender)
""")

# 4) app/services/reply_engine.py (Default -> gemini-2.5-pro)
write_file("app/services/reply_engine.py", """
import os
import logging

logger = logging.getLogger("reply_engine")
logger.setLevel(logging.INFO)

def generate_reply(subject: str, body: str) -> str:
    model_name = os.getenv("GEMINI_MODEL", "models/gemini-2.5-pro")
    api_key = os.getenv("GEMINI_API_KEY")
    try:
        if not api_key:
            raise ValueError("No GEMINI_API_KEY")
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        prompt = f"Subject: {subject}\\nBody: {body}\\n\\nWrite a concise, helpful reply email in a professional tone."
        resp = model.generate_content(prompt)
        return (resp.text or "").strip()
    except Exception as e:
        logger.warning(f"[Gemini] fallback due to: {e}")
        return f"Hi, thanks for your message about '{subject}'. We'll get back to you shortly!"
""")

# 5) app/main.py
write_file("app/main.py", """
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
    print("\\n🔍 Startup Check")
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

    print("--------------------------------------------------\\n")
    notify_slack("🚀 AI Email SaaS started.")

@app.get("/")
def root(): return {"status": "ok", "message": "AI Email SaaS API online"}

@app.get("/health")
def health(): return {"status": "ok", "message": "Server healthy and running"}

app.include_router(routes_gmail_demo.router)
""")

# 6) start.sh
write_file("start.sh", """
#!/bin/bash
echo "🚀 Starting AI Email SaaS..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 10000
""")
os.system("chmod +x start.sh")

# 7) requirements.txt
write_file("requirements.txt", """
fastapi
uvicorn
python-dotenv
pydantic-settings
requests
google-auth
google-auth-oauthlib
google-api-python-client
google-auth-httplib2
""")

# 8) render.yaml
write_file("render.yaml", """
services:
  - type: web
    name: ai-email-saas
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: bash start.sh
    envVars:
      - key: APP_API_KEY
        sync: false
      - key: X_API_KEY
        sync: false
      - key: GEMINI_API_KEY
        sync: false
      - key: GEMINI_MODEL
        value: models/gemini-2.5-pro
      - key: GMAIL_OAUTH_CLIENT_JSON
        sync: false
      - key: EMAIL_SENDER_OVERRIDE
        sync: false
      - key: SLACK_WEBHOOK
        sync: false
      - key: DATABASE_URL
        sync: false
    disks:
      - name: data
        mountPath: /data
        sizeGB: 1
""")

# 9) .env (local template; override sensitive values!)
write_file(".env", f"""
APP_ENV=production
APP_API_KEY=uhofx6UwIt2EQRZBuSzM0u32FXD5wQvVx5jAy4wTWeo
X_API_KEY=uhofx6UwIt2EQRZBuSzM0u32FXD5wQvVx5jAy4wTWeo

EMAIL_SENDER_OVERRIDE=rhettlohts@gmail.com

AI_PROVIDER=gemini
GEMINI_API_KEY=YOUR_REAL_GEMINI_KEY
GEMINI_MODEL=models/gemini-2.5-pro

GMAIL_OAUTH_CLIENT_JSON={ROOT}/gmail_oauth_client.json
GMAIL_TOKEN_PATH={ROOT}/token.json

BASE_URL=https://ai-email-bot-0xut.onrender.com
APP_URL=https://ai-email-bot-0xut.onrender.com
ALLOWED_ORIGINS=*
DEBUG=False
""")

print("\n🎯 Done! Your SaaS project is now production-ready.")
print("Run locally with:\n")
print("   uvicorn app.main:app --host 0.0.0.0 --port 10000\n")
print("Then test with:\n")
print("   curl http://localhost:10000/health\n")
