import time, subprocess, sys, requests, os

WEBHOOK = os.getenv("DISCORD_WEBHOOK")

def run_fix():
    print("🩺 Running fix_all.py...")
    subprocess.run([sys.executable, "fix_all.py"])

def start_server():
    return subprocess.Popen(["uvicorn", "main:app", "--reload"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

while True:
    print("🚀 Launching THE13TH server with watchdog...")
    p = start_server()
    for line in p.stdout:
        print(line, end="")
        if any(err in line for err in ["Traceback", "Error", "Exception"]):
            print("⚠️ Crash detected! Triggering repair...")
            if WEBHOOK:
                requests.post(WEBHOOK, json={"content": "🚨 **Server crashed, auto-repair triggered**"})
            p.kill()
            run_fix()
            break
    time.sleep(3)
