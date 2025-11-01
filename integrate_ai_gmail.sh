#!/bin/bash
set -e

BASE_DIR="app/services"
API_DIR="app/api"

echo "🚀 Integrating AI Reply Engine + Gmail Service..."

# ---------- services/reply_engine.py ----------
cat > $BASE_DIR/reply_engine.py <<'EOF'
"""
AI Reply Engine — generates smart Gmail replies using OpenAI or Gemini.
Falls back to template-based logic if APIs are not available.
"""

import os
from openai import OpenAI
import google.generativeai as genai

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize clients if keys are available
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def generate_reply(subject: str, body: str) -> str:
    """
    Returns a draft AI-generated reply.
    Uses OpenAI if available, otherwise Gemini, otherwise template fallback.
    """
    print(f"⚙️ Generating reply for subject: {subject}")

    # --- 1. Try OpenAI ---
    if openai_client:
        try:
            completion = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an AI email assistant for real estate agents."},
                    {"role": "user", "content": f"Subject: {subject}\n\n{body}\n\nDraft a friendly, professional reply."}
                ],
                max_tokens=300
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"[OpenAI] ❌ Failed: {e}")

    # --- 2. Try Gemini ---
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(f"Subject: {subject}\n\n{body}\n\nDraft a professional, helpful email reply.")
            return response.text.strip()
        except Exception as e:
            print(f"[Gemini] ❌ Failed: {e}")

    # --- 3. Fallback ---
    print("⚠️ No AI key configured; using template fallback.")
    return f"Hi, thanks for your message about '{subject}'. We'll get back to you shortly!"
EOF

# ---------- services/gmail_service.py ----------
cat > $BASE_DIR/gmail_service.py <<'EOF'
"""
Gmail Service — sends or drafts emails using Gmail API.
Supports both live mode and safe demo (draft-only) mode.
"""

import base64
import os
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

DEMO_OUTBOUND_SEND = os.getenv("DEMO_OUTBOUND_SEND", "false").lower() == "true"
GMAIL_TOKEN_B64 = os.getenv("GMAIL_TOKEN_B64")

def _get_gmail_service():
    if not GMAIL_TOKEN_B64:
        raise ValueError("Missing GMAIL_TOKEN_B64 in environment.")
    token_bytes = base64.b64decode(GMAIL_TOKEN_B64)
    creds = Credentials.from_authorized_user_info(eval(token_bytes.decode("utf-8")), scopes=["https://www.googleapis.com/auth/gmail.modify"])
    return build("gmail", "v1", credentials=creds)

def draft_or_send_email(to: str, subject: str, body: str, sender: str | None = None):
    service = _get_gmail_service()

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    if sender:
        message["from"] = sender

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    message_obj = {"raw": raw}

    if DEMO_OUTBOUND_SEND:
        # send immediately
        sent = service.users().messages().send(userId="me", body=message_obj).execute()
        return {"status": "sent", "id": sent.get("id")}
    else:
        # create draft only
        draft = service.users().drafts().create(userId="me", body={"message": message_obj}).execute()
        return {"status": "drafted", "id": draft.get("id")}
EOF

# ---------- api/routes_gmail_demo.py ----------
cat > $API_DIR/routes_gmail_demo.py <<'EOF'
from fastapi import APIRouter
from pydantic import BaseModel
from ..core.config import settings
from ..services.reply_engine import generate_reply
from ..services.gmail_service import draft_or_send_email

router = APIRouter()

class DemoReplyIn(BaseModel):
    subject: str
    body: str
    customer_email: str

@router.post("/draft-reply")
def draft_reply(payload: DemoReplyIn):
    """Generate AI-powered Gmail reply and either draft or send based on .env flag."""
    reply = generate_reply(payload.subject, payload.body)
    try:
        result = draft_or_send_email(
            to=payload.customer_email,
            subject=f"Re: {payload.subject}",
            body=reply,
            sender=settings.EMAIL_SENDER_OVERRIDE
        )
        return {**result, "reply": reply, "to": payload.customer_email}
    except Exception as e:
        return {"status": "error", "error": str(e), "reply": reply}
EOF

echo "✅ Integrated AI Reply Engine + Gmail Service successfully!"
echo "👉 Next: update .env with your OpenAI or Gemini API key, and Gmail token JSON (base64)."
