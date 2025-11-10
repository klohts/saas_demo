import os
import smtplib
import requests
from email.message import EmailMessage
from fastapi import FastAPI, HTTPException

app = FastAPI(title="SMTP Health & Alert")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")

def notify_discord(msg: str):
    if not DISCORD_WEBHOOK:
        print("⚠️ No Discord webhook configured")
        return
    try:
        requests.post(DISCORD_WEBHOOK, json={"content": msg}, timeout=8)
    except Exception as e:
        print("Discord alert failed:", e)


def send_test_email(to="test@example.com"):
    try:
        print("📡 Connecting to SMTP...")
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)

        msg = EmailMessage()
        msg["Subject"] = "✅ SMTP Health Check Successful"
        msg["From"] = SMTP_FROM
        msg["To"] = to
        msg.set_content("Your SMTP server is configured correctly and working.")

        server.send_message(msg)
        server.quit()
        print("✅ Email sent successfully")

        return True, "Email sent"
    except Exception as e:
        err = str(e)
        print("❌ SMTP Failed:", err)
        notify_discord(f"�� SMTP HEALTH ALERT\nError: {err}")
        return False, err


@app.get("/smtp/health")
def smtp_health():
    ok, detail = send_test_email(SMTP_USER)
    if not ok:
        raise HTTPException(status_code=500, detail=detail)
    return {"status": "healthy", "detail": detail}


if __name__ == "__main__":
    send_test_email(SMTP_USER)
