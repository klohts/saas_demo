#!/usr/bin/env python3
"""
deploy_guardian_v4_autoid.py — Self-Healing Deploy Automation
--------------------------------------------------------------
✅ Syntax/import validation
✅ Git push → Render auto-deploy
✅ Auto-detect Render service ID
✅ Deploy monitor + endpoint verification
✅ Postgres logging
✅ Optional email + Slack notifications
"""

import os, subprocess, requests, json, time, psycopg2, sys, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# === Load Environment ===
load_dotenv(dotenv_path="/home/hp/AIAutomationProjects/saas_demo/.env")

RENDER_API_KEY = os.getenv("RENDER_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
APP_URL = os.getenv("APP_URL", "https://ai-email-bot-0xut.onrender.com")

# Notification credentials
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK")

# Target service name (as seen in Render dashboard)
SERVICE_NAME = os.getenv("RENDER_SERVICE_NAME", "saas-demo-app")

if not RENDER_API_KEY:
    print("❌ Missing RENDER_API_KEY in .env")
    sys.exit(1)

headers = {"Authorization": f"Bearer {RENDER_API_KEY}"}

# ===========================================================
#  STEP 0 — AUTO-DETECT SERVICE ID
# ===========================================================
def get_service_id():
    print(f"🔍 Auto-detecting Render service ID for '{SERVICE_NAME}' ...")
    try:
        resp = requests.get("https://api.render.com/v1/services", headers=headers, timeout=15)
        if resp.status_code != 200:
            print("⚠️ Unable to fetch services from Render:", resp.text)
            return None

        data = resp.json()
        for svc in data:
            name = svc.get("service", {}).get("name") or svc.get("name")
            sid = svc.get("service", {}).get("id") or svc.get("id")
            if name and SERVICE_NAME.lower() in name.lower():
                print(f"✅ Found service '{name}' (ID: {sid})")
                return sid

        print("⚠️ No matching service found for", SERVICE_NAME)
        return None
    except Exception as e:
        print("❌ Error fetching service ID:", e)
        return None

# ===========================================================
#  STEP 1 — VALIDATE SYNTAX & IMPORTS
# ===========================================================
def validate_code():
    print("🧪 Validating Python files under saas_demo/ ...")
    for root, _, files in os.walk("saas_demo"):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                result = subprocess.run(
                    ["python3", "-m", "py_compile", path],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    print(f"❌ Syntax error in {path}:\n{result.stderr}")
                    sys.exit(1)
    print("✅ All Python files passed syntax check.\n")

    try:
        subprocess.check_call(["python3", "-c", "from app import main"], cwd=os.path.dirname(__file__))
        print("✅ Import test passed for main app.\n")
    except subprocess.CalledProcessError as e:
        print("❌ Import failed:", e)
        sys.exit(1)

# ===========================================================
#  STEP 2 — GIT PUSH
# ===========================================================
def trigger_git_push():
    print("📦 Committing and pushing changes to GitHub...")
    os.system("git add .")
    os.system("git commit -m 'Auto-deploy via Deploy Guardian v4' || echo 'No new changes'")
    os.system("git push origin main")
    print("✅ Git push completed. Render will auto-deploy.\n")

# ===========================================================
#  STEP 3 — MONITOR RENDER DEPLOY
# ===========================================================
def monitor_render_deploy(service_id):
    print(f"🔍 Monitoring Render deploy for service ID: {service_id}\n")
    url = f"https://api.render.com/v1/services/{service_id}/deploys"

    for attempt in range(20):
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            print(f"⚠️ Poll {attempt}: HTTP {r.status_code}")
            time.sleep(10)
            continue

        try:
            data = r.json()
        except json.JSONDecodeError:
            print("⚠️ Non-JSON response (Render free-tier limit).")
            break

        if isinstance(data, list) and data:
            deploy = data[0].get("deploy", data[0])
            status = deploy.get("status", "unknown")
            print(f"⏳ Deploy status: {status}")
            if status in ["live", "update_live", "succeeded"]:
                print("🎉 Deploy succeeded!\n")
                return True
            if status in ["failed", "update_failed"]:
                print("❌ Deploy failed on Render.")
                return False
        time.sleep(10)
    print("⚠️ Timeout: Could not confirm deploy status.")
    return False

# ===========================================================
#  STEP 4 — VERIFY LIVE APP
# ===========================================================
def verify_live_app():
    print("🌐 Verifying live app endpoints...\n")
    try:
        health = requests.get(f"{APP_URL}/health", timeout=15)
        if health.status_code == 200 and "ok" in health.text:
            print("✅ /health endpoint: OK")
        else:
            print("❌ /health failed:", health.text)
            return False

        payload = {
            "subject": "Viewing request",
            "body": "I’d like to see your property at Banana Island",
            "sender": "buyer@example.com",
        }
        resp = requests.post(f"{APP_URL}/generate-reply", json=payload, timeout=20)
        if resp.status_code == 200:
            print("✅ /generate-reply endpoint:", resp.json())
            return True
        else:
            print("❌ /generate-reply failed:", resp.text)
            return False
    except Exception as e:
        print("❌ Verification error:", e)
        return False

# ===========================================================
#  STEP 5 — LOG RESULT TO POSTGRES
# ===========================================================
def log_deploy_result(status: str, message: str):
    if not DATABASE_URL:
        print("⚠️ DATABASE_URL not set — skipping DB logging.")
        return
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS deploy_logs (
                id SERIAL PRIMARY KEY,
                deployed_at TIMESTAMP DEFAULT NOW(),
                status TEXT,
                message TEXT
            );
        """)
        cur.execute("INSERT INTO deploy_logs (status, message) VALUES (%s, %s);", (status, message))
        conn.commit()
        conn.close()
        print(f"🪵 Logged deploy result to database: {status}")
    except Exception as e:
        print("⚠️ Failed to log to DB:", e)

# ===========================================================
#  STEP 6 — NOTIFICATIONS
# ===========================================================
def send_email(subject, body):
    if not SMTP_USER or not SMTP_PASS or not NOTIFY_EMAIL:
        print("⚠️ Email notifications not configured.")
        return
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = NOTIFY_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print("📧 Email notification sent.")
    except Exception as e:
        print("⚠️ Email notification failed:", e)

def send_slack(message):
    if not SLACK_WEBHOOK:
        print("⚠️ Slack webhook not set.")
        return
    try:
        requests.post(SLACK_WEBHOOK, json={"text": message})
        print("💬 Slack notification sent.")
    except Exception as e:
        print("⚠️ Slack notification failed:", e)

# ===========================================================
#  MAIN
# ===========================================================
if __name__ == "__main__":
    print("🚀 Starting Deploy Guardian v4.0 (Auto-ID)...\n")

    validate_code()
    trigger_git_push()

    service_id = get_service_id()
    if not service_id:
        print("❌ Unable to auto-detect Render service ID.")
        sys.exit(1)

    success = monitor_render_deploy(service_id)

    if success:
        verified = verify_live_app()
        status = "success" if verified else "partial"
        message = "✅ App verified live" if verified else "⚠️ Deploy succeeded but verification failed"
        log_deploy_result(status, message)
        send_email("Render Deploy: SUCCESS ✅", message)
        send_slack(f"🚀 *Deploy Success* — {message}")
    else:
        log_deploy_result("failed", "Render deploy failed ❌")
        send_email("Render Deploy: FAILED ❌", "Render deploy failed. Check logs.")
        send_slack("💥 *Render Deploy FAILED!* — Please investigate.")

    print("\n✅ Deploy Guardian v4.0 finished.\n")
