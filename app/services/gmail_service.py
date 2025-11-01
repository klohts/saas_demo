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
    return create_draft(service, to, subject, body_text, sender) if dry_run         else send_email(service, to, subject, body_text, sender)
