"""
SaaSReplyAgent — single-file server
Location: app/saasreply_server.py

Features:
- /health
- /api/auto-reply (POST) with JSON body: {max_messages, dry_run, model_override, skip_senders[]}
- /api/cron/auto-reply (GET) for Render Cron
- X-API-Key authentication (env: APP_API_KEY)
- Gmail via OAuth (personal) or Service Account DWD (Workspace) (env: GMAIL_AUTH_MODE)
- Gemini 2.5 integration with model auto-detect and overrides
- Cooldown to avoid repeated triggers
"""

import os
import time
import base64
import pickle
from typing import Optional, List

from fastapi import FastAPI, APIRouter, Depends, Header, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------- Gmail / Google API imports ----------
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# ---------- Gemini ----------
import google.generativeai as genai

# =========================
# Paths & Global Config
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS_DIR = os.path.join(BASE_DIR, "keys")
os.makedirs(KEYS_DIR, exist_ok=True)

SERVICE_ACCOUNT_FILE = os.path.join(KEYS_DIR, "saasreplyagent-key.json")
OAUTH_CLIENT_FILE = os.path.join(KEYS_DIR, "credentials.json")
TOKEN_FILE = os.path.join(KEYS_DIR, "token.pkl")

# Gmail scopes
SCOPES = [
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
]

# =========================
# API Security
# =========================
def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    expected = os.getenv("APP_API_KEY")
    if not expected:
        raise HTTPException(status_code=500, detail="Server missing APP_API_KEY")
    if not x_api_key or x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")

# =========================
# Gmail Connector (OAuth or SA)
# =========================
def get_gmail_service(subject: Optional[str] = None):
    """Return an authenticated Gmail service using OAuth or Service Account."""
    mode = os.getenv("GMAIL_AUTH_MODE", "oauth").strip().lower()
    creds = None

    if mode == "service_account":
        # Workspace Domain-Wide Delegation path
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            raise RuntimeError(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")
        if not subject:
            # You can pass subject per-call if you need to impersonate a specific user
            subject = os.getenv("GMAIL_IMPERSONATE_SUBJECT", "").strip()
            if not subject:
                raise RuntimeError("GMAIL_IMPERSONATE_SUBJECT not set for service_account mode.")
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES, subject=subject
        )
        print(f"✅ Using service account for {subject}")
    else:
        # OAuth (personal Gmail) path
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(OAUTH_CLIENT_FILE):
                    raise RuntimeError(f"OAuth client file not found: {OAUTH_CLIENT_FILE}")
                flow = InstalledAppFlow.from_client_secrets_file(OAUTH_CLIENT_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            # persist
            with open(TOKEN_FILE, "wb") as token:
                pickle.dump(creds, token)
            print("✅ OAuth login complete; token saved to keys/token.pkl")

    return build("gmail", "v1", credentials=creds)

def send_email(service, to: str, subject: str, body_text: str):
    """Send plain text email via Gmail API."""
    message = MIMEText(body_text)
    message["to"] = to
    message["subject"] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    try:
        sent = service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
        print(f"✅ Email sent to {to}. Message ID: {sent.get('id')}")
        return sent
    except HttpError as e:
        print(f"❌ Failed to send email: {e}")
        return None

def list_messages(service, query: Optional[str] = None, max_results: int = 10):
    """List messages matching the query (default unread)."""
    try:
        results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
        messages = results.get("messages", [])
        print(f"📨 Found {len(messages)} messages.")
        return messages
    except HttpError as e:
        print(f"❌ Failed to list messages: {e}")
        return []

def read_message(service, msg_id: str):
    """Fetch a full message by ID."""
    try:
        msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        return msg
    except HttpError as e:
        print(f"❌ Failed to read message {msg_id}: {e}")
        return None

# =========================
# Gemini Setup & Agent Logic
# =========================
def validate_gemini_key():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise EnvironmentError(
            "❌ GEMINI_API_KEY not found. Export it, e.g.\n"
            "   export GEMINI_API_KEY='AIza...your_key...'"
        )
    print(f"🔑 Gemini API key detected (length {len(key)}).")

def get_best_model() -> str:
    """Pick the best available model; allow override via AI_MODEL_OVERRIDE env."""
    override = os.getenv("AI_MODEL_OVERRIDE", "").strip()
    if override:
        return override
    try:
        names = [m.name for m in genai.list_models()]
        # preferred in order:
        for candidate in [
            "models/gemini-2.5-flash",
            "models/gemini-flash-latest",
            "models/gemini-2.5-pro",
            "models/gemini-pro-latest",
            "models/gemini-pro",
        ]:
            if candidate in names:
                return candidate
    except Exception:
        pass
    return "models/gemini-2.5-flash"

def setup_gemini():
    validate_gemini_key()
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model_name = get_best_model()
    print(f"🧠 Using Gemini model: {model_name}")
    return genai.GenerativeModel(model_name), model_name

def summarize_and_reply():
    """Core agent: reads unread, drafts via Gemini, replies, marks read."""
    model, _ = setup_gemini()
    service = get_gmail_service()

    # pull invocation settings
    max_messages = int(os.getenv("AI_MAX_MESSAGES", "5"))
    dry_run = os.getenv("AI_DRY_RUN", "0") == "1"
    skip_list = [s.strip().lower() for s in os.getenv(
        "AI_SKIP_SENDERS", "no-reply@,noreply@,mailer-daemon@"
    ).split(",") if s.strip()]

    messages = list_messages(service, query="is:unread", max_results=max_messages)
    if not messages:
        print("📭 No unread messages found.")
        return

    for msg in messages:
        msg_id = msg["id"]
        data = read_message(service, msg_id)
        if not data:
            continue

        snippet = data.get("snippet", "")
        headers = data["payload"].get("headers", [])
        subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No subject")
        sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "Unknown sender")

        if any(s in sender.lower() for s in skip_list):
            print(f"⏩ Skipping sender by filter {skip_list}: {sender}")
            continue

        print(f"\n📨 Processing from {sender} | Subject: {subject}")

        prompt = f"""
        You are a succinct professional email assistant.
        Read the message and draft a friendly, helpful reply under 100 words.
        Keep it context-aware but avoid hallucinations; reflect uncertainty if details are missing.

        Message:
        {snippet}
        """

        try:
            resp = model.generate_content(prompt)
            ai_reply = (resp.text or "").strip()
            if not ai_reply:
                print("⚠️ Empty AI reply, skipping.")
                continue
        except Exception as e:
            print(f"❌ Gemini generation error: {e}")
            continue

        if dry_run:
            print(f"🤖 [DRY RUN] Would reply to {sender} with: {ai_reply[:120]}...")
        else:
            ok = send_email(service, to=sender, subject=f"Re: {subject}", body_text=ai_reply)
            if not ok:
                continue

        try:
            service.users().messages().modify(
                userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            print(f"✅ Marked as read: {sender}")
        except Exception as e:
            print(f"⚠️ Label update failed: {e}")

        time.sleep(2)  # gentle rate limit

# =========================
# FastAPI App & Routes
# =========================
app = FastAPI(title="SaaSReplyAgent Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # tighten for production (dashboard origin)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(prefix="/api", tags=["auto-reply"])

# simple in-process cooldown
_LAST_RUN_AT = 0.0
_COOLDOWN_SECONDS = int(os.getenv("AUTO_REPLY_COOLDOWN_SECONDS", "30"))

class AutoReplyRequest(BaseModel):
    max_messages: int = Field(default=5, ge=1, le=50)
    dry_run: bool = False
    model_override: Optional[str] = None
    skip_senders: List[str] = Field(default_factory=list)

class AutoReplyResponse(BaseModel):
    status: str
    used_model: str
    max_messages: int
    dry_run: bool
    cooldown_seconds: int
    message: str

@app.get("/health")
def health():
    return {"status": "ok"}

@router.post("/auto-reply", response_model=AutoReplyResponse)
def trigger_auto_reply(
    payload: AutoReplyRequest = Body(...),
    _: None = Depends(require_api_key),
):
    global _LAST_RUN_AT
    now = time.time()
    remaining = _COOLDOWN_SECONDS - (now - _LAST_RUN_AT)
    if remaining > 0:
        return AutoReplyResponse(
            status="cooldown",
            used_model="n/a",
            max_messages=payload.max_messages,
            dry_run=payload.dry_run,
            cooldown_seconds=int(remaining),
            message=f"Try again in {int(remaining)}s",
        )

    # pass options via env for the agent
    os.environ["AI_MAX_MESSAGES"] = str(payload.max_messages)
    os.environ["AI_MODEL_OVERRIDE"] = payload.model_override or ""
    os.environ["AI_SKIP_SENDERS"] = ",".join(payload.skip_senders) if payload.skip_senders else os.getenv(
        "AI_SKIP_SENDERS", "no-reply@,noreply@,mailer-daemon@"
    )
    if payload.dry_run:
        os.environ["AI_DRY_RUN"] = "1"
    else:
        os.environ.pop("AI_DRY_RUN", None)

    # sanity checks (will raise helpful errors if misconfigured)
    model, used_model = setup_gemini()
    _ = get_gmail_service()

    summarize_and_reply()

    _LAST_RUN_AT = time.time()
    return AutoReplyResponse(
        status="ok",
        used_model=used_model,
        max_messages=payload.max_messages,
        dry_run=payload.dry_run,
        cooldown_seconds=_COOLDOWN_SECONDS,
        message="Auto-reply completed",
    )

@router.get("/cron/auto-reply", response_model=AutoReplyResponse)
def cron_auto_reply(_: None = Depends(require_api_key)):
    # default safer values for unattended runs
    os.environ["AI_MAX_MESSAGES"] = os.getenv("AI_MAX_MESSAGES", "5")
    os.environ.pop("AI_DRY_RUN", None)
    os.environ["AI_SKIP_SENDERS"] = os.getenv("AI_SKIP_SENDERS", "no-reply@,noreply@,mailer-daemon@")

    model, used_model = setup_gemini()
    _ = get_gmail_service()
    summarize_and_reply()

    return AutoReplyResponse(
        status="ok",
        used_model=used_model,
        max_messages=int(os.getenv("AI_MAX_MESSAGES", "5")),
        dry_run=False,
        cooldown_seconds=_COOLDOWN_SECONDS,
        message="Cron auto-reply completed",
    )

app.include_router(router)

# ============ Optional local runner ============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.saasreply_server:app", host="0.0.0.0", port=10000, reload=True)
