#!/usr/bin/env python3
"""
gmail_agent_mvp.py
MVP Gmail agent (Service Account + Domain-wide delegation)

Place: /home/hp/AIAutomationProjects/saas_demo/gmail_agent_mvp.py
Requires:
  - GMAIL_SERVICE_JSON in .env (service account JSON)
  - GMAIL_USER in .env (user to impersonate; must be in your Workspace domain)
  - APP_URL in .env (your /generate-reply endpoint)
  - Optional: DATABASE_URL in .env (for logging)

Behavior:
  - Connects to Gmail as service account impersonating GMAIL_USER
  - Lists unread messages, fetches body, calls APP_URL/generate-reply
  - Sends reply via Gmail, marks message as read and labels it "Replied-By-Bot"
  - Logs to console and to Postgres if DATABASE_URL provided
"""

import os
import base64
import email
import time
import json
import logging
from typing import Optional
from email.mime.text import MIMEText

import requests
import psycopg2
from dotenv import load_dotenv

# Google libraries
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Config & logging ---
load_dotenv(dotenv_path="/home/hp/AIAutomationProjects/saas_demo/.env")

GMAIL_SERVICE_JSON = os.getenv("GMAIL_SERVICE_JSON")
GMAIL_USER = os.getenv("GMAIL_USER")
APP_URL = os.getenv("APP_URL", "https://ai-email-bot-0xut.onrender.com")
DATABASE_URL = os.getenv("DATABASE_URL")

if not GMAIL_SERVICE_JSON or not GMAIL_USER:
    raise SystemExit("ERROR: Please set GMAIL_SERVICE_JSON and GMAIL_USER in your .env")

SCOPES = [
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- Utility: create Gmail service with domain-wide delegation ---
def build_gmail_service():
    logging.info("Building Gmail service using service account JSON: %s", GMAIL_SERVICE_JSON)
    creds = service_account.Credentials.from_service_account_file(
        GMAIL_SERVICE_JSON, scopes=SCOPES
    )
    # Impersonate the user (requires domain-wide delegation configured by admin)
    delegated_creds = creds.with_subject(GMAIL_USER)
    service = build("gmail", "v1", credentials=delegated_creds, cache_discovery=False)
    return service

# --- Helpers for message parsing and creation ---
def get_unread_message_ids(service, label_ids=None, max_results=10):
    try:
        query = "is:unread -from:me"
        resp = service.users().messages().list(userId="me", q=query, labelIds=label_ids or []).execute()
        msgs = resp.get("messages", [])
        return [m["id"] for m in msgs]
    except HttpError as e:
        logging.error("Gmail list error: %s", e)
        return []

def fetch_message(service, msg_id):
    try:
        msg = service.users().messages().get(userId="me", id=msg_id, format="raw").execute()
        raw = base64.urlsafe_b64decode(msg["raw"].encode("ASCII"))
        mime_msg = email.message_from_bytes(raw)
        headers = {k: v for k, v in mime_msg.items()}
        # get body (prefers text/plain)
        body = ""
        if mime_msg.is_multipart():
            for part in mime_msg.walk():
                ctype = part.get_content_type()
                cdisp = str(part.get("Content-Disposition"))
                if ctype == "text/plain" and "attachment" not in cdisp:
                    body = part.get_payload(decode=True).decode(errors="replace")
                    break
        else:
            body = mime_msg.get_payload(decode=True).decode(errors="replace")
        return {"id": msg_id, "headers": headers, "body": body, "threadId": msg.get("threadId")}
    except Exception as e:
        logging.error("Failed to fetch message %s: %s", msg_id, e)
        return None

def create_reply_message(original_headers, reply_body, from_email):
    # Build headers for in-reply-to and references
    msg = MIMEText(reply_body, "plain")
    subject = original_headers.get("Subject", "")
    if not subject.lower().startswith("re:"):
        msg["Subject"] = "Re: " + subject
    else:
        msg["Subject"] = subject
    msg["To"] = original_headers.get("From")
    msg["From"] = from_email
    if original_headers.get("Message-ID"):
        msg["In-Reply-To"] = original_headers.get("Message-ID")
        msg["References"] = original_headers.get("Message-ID")
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw}

def send_message(service, raw_message):
    try:
        sent = service.users().messages().send(userId="me", body=raw_message).execute()
        return sent
    except HttpError as e:
        logging.error("Failed to send message: %s", e)
        return None

def ensure_label(service, label_name="Replied-By-Bot"):
    try:
        labels = service.users().labels().list(userId="me").execute().get("labels", [])
        for l in labels:
            if l["name"] == label_name:
                return l["id"]
        # create label
        body = {"name": label_name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
        created = service.users().labels().create(userId="me", body=body).execute()
        return created["id"]
    except Exception as e:
        logging.error("Label error: %s", e)
        return None

def mark_as_replied(service, message_id, replied_label_id):
    try:
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"], "addLabelIds": [replied_label_id]},
        ).execute()
        logging.info("Marked message %s as read and labeled with %s", message_id, replied_label_id)
    except Exception as e:
        logging.error("Failed to modify labels on %s: %s", message_id, e)

# --- Logging to Postgres (optional) ---
def log_to_db(status, message, subject=None, sender=None):
    if not DATABASE_URL:
        return
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gmail_agent_logs (
                id SERIAL PRIMARY KEY,
                logged_at TIMESTAMP DEFAULT NOW(),
                status TEXT,
                details TEXT,
                subject TEXT,
                sender TEXT
            );
        """)
        cur.execute("INSERT INTO gmail_agent_logs (status, details, subject, sender) VALUES (%s, %s, %s, %s)",
                    (status, message, subject, sender))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logging.warning("DB log failed: %s", e)

# --- Call your AI endpoint to generate a reply ---
def generate_reply_via_ai(subject, body, sender):
    endpoint = APP_URL.rstrip("/") + "/generate-reply"
    payload = {"subject": subject, "body": body, "sender": sender}
    try:
        r = requests.post(endpoint, json=payload, timeout=20)
        r.raise_for_status()
        # expect JSON like {"reply": "..."} or {"reply": "...", ...}
        data = r.json()
        # attempt multiple keys
        reply = data.get("reply") or data.get("message") or data.get("reply_text") or str(data)
        return reply
    except Exception as e:
        logging.error("AI endpoint error: %s", e)
        return None

# --- Main loop: fetch unread, generate reply, send, label, log ---
def process_inbox(max_messages=10):
    service = build_gmail_service()
    label_id = ensure_label(service, "Replied-By-Bot") or None
    msg_ids = get_unread_message_ids(service, max_results=max_messages)
    if not msg_ids:
        logging.info("No unread messages found.")
        return

    for mid in msg_ids:
        logging.info("Processing message id=%s", mid)
        msg = fetch_message(service, mid)
        if not msg:
            continue
        headers = msg["headers"]
        sender = headers.get("From", "")
        subject = headers.get("Subject", "(no subject)")
        body = msg["body"] or ""
        logging.info("From: %s | Subject: %s", sender, subject)

        # Call AI to generate reply
        reply_text = generate_reply_via_ai(subject, body, sender)
        if not reply_text:
            logging.error("Skipping message %s — AI did not return a reply", mid)
            log_to_db("ai_failed", "AI did not return reply", subject, sender)
            continue

        # Create reply message and send
        raw = create_reply_message(headers, reply_text, GMAIL_USER)
        sent = send_message(service, raw)
        if sent:
            logging.info("Replied to %s (msgId=%s)", sender, sent.get("id"))
            if label_id:
                mark_as_replied(service, mid, label_id)
            log_to_db("replied", f"Replied (sent_id={sent.get('id')})", subject, sender)
        else:
            logging.error("Failed to send reply to %s", sender)
            log_to_db("send_failed", "Failed to send via Gmail API", subject, sender)

# --- Standalone run (single pass) ---
if __name__ == "__main__":
    logging.info("Starting gmail_agent_mvp — single-pass run")
    try:
        process_inbox(max_messages=20)
        logging.info("Run complete.")
    except Exception as exc:
        logging.exception("Unhandled error in gmail_agent_mvp: %s", exc)
