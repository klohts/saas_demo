#!/usr/bin/env python3
"""
Stage 13.1 — Magic Link Email Delivery for THE13TH
Adds secure outbound email via Gmail SMTP.
"""

import os, smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

CONFIG_FILE = Path(".env")

def patch_magiclink():
    utils_path = Path("utils/auth_magic.py")
    code = utils_path.read_text().splitlines()

    if any("send_magic_link_email" in l for l in code):
        print("✅  Email function already present.")
        return

    snippet = """
import smtplib, ssl, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_magic_link_email(recipient: str, magic_link: str):
    sender = os.getenv("SMTP_SENDER")
    password = os.getenv("SMTP_PASSWORD")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 465))

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "🔮 Your THE13TH Magic Login Link"
    msg["From"] = sender
    msg["To"] = recipient

    html = f\"""<html><body style='font-family:sans-serif'>
    <h2>Welcome to THE13TH</h2>
    <p>Click below to log in:</p>
    <p><a href='{magic_link}'>{magic_link}</a></p>
    <p><em>This link expires in 15 minutes.</em></p>
    </body></html>\""" 

    msg.attach(MIMEText(html, "html"))
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())
    print(f"📧  Magic link sent → {recipient}")
"""
    code.extend(snippet.splitlines())
    utils_path.write_text("\n".join(code))
    print("🧩  Patched utils/auth_magic.py with send_magic_link_email().")

def patch_main():
    path = Path("main.py")
    text = path.read_text()
    if "send_magic_link_email(" in text:
        print("✅  main.py already patched.")
        return

    insert = """
    # Send email if SMTP env vars are set
    from utils.auth_magic import send_magic_link_email
    if os.getenv("SMTP_SENDER") and os.getenv("SMTP_PASSWORD"):
        try:
            send_magic_link_email(email, link)
        except Exception as e:
            print(f"⚠️ Email failed: {e}")
"""
    new = text.replace("return {\"email\": email, \"magic_link\": link}", 
                       f"return {{\"email\": email, \"magic_link\": link}}{insert}")
    path.write_text(new)
    print("🧩  main.py patched to auto-email magic link.")

def ensure_env():
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text("# SMTP config for THE13TH Magic Link\n")
    env = CONFIG_FILE.read_text()
    if "SMTP_SENDER" not in env:
        env += (
            "\n# Add your Gmail SMTP credentials\n"
            "SMTP_SENDER=yourname@gmail.com\n"
            "SMTP_PASSWORD=app_password_here\n"
            "SMTP_HOST=smtp.gmail.com\n"
            "SMTP_PORT=465\n"
        )
        CONFIG_FILE.write_text(env)
        print("⚙️  .env updated with SMTP placeholders.")

if __name__ == "__main__":
    patch_magiclink()
    patch_main()
    ensure_env()
    print("✅ Stage 13.1 email delivery layer ready. Restart Uvicorn to apply.")
