"""
ai_reply_agent.py
---------------------------------------------------
Gemini 2.5-powered AI auto-reply agent for SaaSReplyAgent.
Handles:
 - Gmail integration (via gmail_service)
 - Smart model and version detection
 - Key validation and graceful error handling
"""

import os
import time
import base64
import google.generativeai as genai
from email.mime.text import MIMEText
from app.services.gmail_service import get_gmail_service, list_messages, read_message, send_email


# ============================================================
# CONFIGURATION
# ============================================================
MAX_MESSAGES = 5
DEFAULT_MODEL = "models/gemini-2.5-flash"
REPLY_LABEL = "AutoReplied"


def get_best_model():
    """Select the best available Gemini model automatically."""
    try:
        available = [m.name for m in genai.list_models()]
        if DEFAULT_MODEL in available:
            return DEFAULT_MODEL
        elif "models/gemini-flash-latest" in available:
            return "models/gemini-flash-latest"
        elif "models/gemini-pro-latest" in available:
            return "models/gemini-pro-latest"
        else:
            # Fallback for very old SDKs
            return "models/gemini-pro"
    except Exception:
        return DEFAULT_MODEL


def validate_gemini_key():
    """Check for valid Gemini API key."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise EnvironmentError(
            "❌ GEMINI_API_KEY not found. Please export it before running:\n"
            "   export GEMINI_API_KEY='AIzaSyYourKeyHere'"
        )
    print(f"🔑 Gemini API key detected (length {len(key)}).")


def setup_gemini():
    """Configure Gemini and select model."""
    validate_gemini_key()
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model_name = get_best_model()
    print(f"🧠 Using Gemini model: {model_name}")
    return genai.GenerativeModel(model_name)


# ============================================================
# CORE AI LOGIC
# ============================================================
def summarize_and_reply():
    """Main function: read unread emails and auto-reply using Gemini."""
    try:
        model = setup_gemini()
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

            # Skip automated senders
            if "no-reply" in sender.lower() or "noreply" in sender.lower():
                print(f"⏩ Skipping automated sender: {sender}")
                continue

            print(f"\n📨 Processing message from {sender} | Subject: {subject}")

            # --------------------------------------------------------
            # Step 1: Generate AI reply
            # --------------------------------------------------------
            try:
                prompt = f"""
                You are an AI email assistant helping respond to professional emails.
                Read the following message and generate a concise, polite reply.
                Keep it under 100 words, friendly, and professional.

                Message:
                {snippet}
                """
                response = model.generate_content(prompt)
                ai_reply = (response.text or "").strip()
                if not ai_reply:
                    print("⚠️ Empty reply generated, skipping.")
                    continue
            except Exception as e:
                print(f"❌ Gemini generation error: {e}")
                continue

            # --------------------------------------------------------
            # Step 2: Send reply via Gmail
            # --------------------------------------------------------
            try:
                send_email(service, to=sender, subject=f"Re: {subject}", body_text=ai_reply)
                print(f"🤖 Replied to {sender}")
            except Exception as e:
                print(f"❌ Failed to send email: {e}")
                continue

            # --------------------------------------------------------
            # Step 3: Mark message as read
            # --------------------------------------------------------
            try:
                service.users().messages().modify(
                    userId="me",
                    id=msg_id,
                    body={"removeLabelIds": ["UNREAD"]}
                ).execute()
                print(f"✅ Marked message from {sender} as read.")
            except Exception as e:
                print(f"⚠️ Could not update labels: {e}")

            time.sleep(2)  # rate limiting

    except Exception as e:
        print(f"🚨 Startup error: {e}")


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    summarize_and_reply()
