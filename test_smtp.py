import smtplib
import os
from email.message import EmailMessage

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_FROM = os.getenv("SMTP_FROM")

# The email you want to send the test to
TEST_TO = SMTP_USER  # Sends to yourself by default

msg = EmailMessage()
msg["Subject"] = "✅ SMTP Test Email"
msg["From"] = SMTP_FROM
msg["To"] = TEST_TO
msg.set_content("If you're reading this, your SMTP setup is working perfectly ��")

try:
    print("🔌 Connecting to SMTP server...")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)

    print(f"✅ Email sent successfully to {TEST_TO}")

except Exception as e:
    print("❌ Failed to send email:")
    print(e)
