"""
ai_reply_agent.py
-------------------------------------
Gemini-powered AI auto-reply system for Gmail.
Imports Gmail connector from gmail_service.py
"""

import os
import time
import base64
from email.mime.text import MIMEText
import google.generativeai as genai
from app.services.gmail_service import get_gmail_service, list_messages, read_message, send_email

# ================================================================
# CONFIGURATION
# ================================================================
MODEL_NAME = "gemini-1.5-flash"
REPLY_LABEL = "AutoReplied"
MAX_MESSAGES = 5  # limit for batch reply

# Initialize Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


# ================================================================
# CORE LOGIC
# ================================================================
def summarize_and_reply():
    """Reads unread emails, summarizes them with Gemini, and sends auto-replies."""
    service = get_gmail_service()
    messages = list_messages(service, query="is:unread", max_results=MAX_MESSAGES)

    if not messages:
        print("📭 No unread messages found.")
        return

    for msg in messages:
        msg_id = msg["id"]
        msg_data = read_message(service, msg_id)
        snippet = msg_data.get("snippet", "")
        headers = msg_data["payload"].get("headers", [])
        subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "No subject")
        sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "Unknown sender")

        print(f"\n📨 Processing message from {sender} | Subject: {subject}")

        # --------------------------------------------------------
        # Step 1: Summarize message content with Gemini
        # --------------------------------------------------------
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            prompt = f"""
            You are an AI email assistant. The following email came from a client.
            Summarize it briefly and generate a polite, professional reply.

            Email:
            {snippet}

            Reply tone: friendly, concise, and relevant.
            """
            response = model.generate_content(prompt)
            ai_reply = response.text.strip()
        except Exception as e:
            print(f"❌ Gemini error: {e}")
            continue

        # --------------------------------------------------------
        # Step 2: Send the AI-generated reply
        # --------------------------------------------------------
        try:
            send_email(service, to=sender, subject=f"Re: {subject}", body_text=ai_reply)
            print(f"🤖 Auto-replied to {sender}")
        except Exception as e:
            print(f"❌ Failed to send reply: {e}")
            continue

        # --------------------------------------------------------
        # Step 3: Mark message as read / label as AutoReplied
        # --------------------------------------------------------
        try:
            service.users().messages().modify(
                userId="me",
                id=msg_id,
                body={"removeLabelIds": ["UNREAD"], "addLabelIds": []}
            ).execute()
            print(f"✅ Marked message from {sender} as read.")
        except Exception as e:
            print(f"⚠️ Could not update labels: {e}")

        time.sleep(2)  # polite delay to avoid API rate limits


# ================================================================
# ENTRY POINT
# ================================================================
if __name__ == "__main__":
    summarize_and_reply()
