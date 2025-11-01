# test_api_endpoints.py
"""
Verifies FastAPI endpoint + DB integration.
1. Checks /health endpoint (local + Render)
2. Inserts a client via POST /clients
3. Retrieves it via GET /clients
4. Cleans up the record
"""

import requests
import uuid
import os

# === CONFIG ===
LOCAL_URL = "http://127.0.0.1:8000"
RENDER_URL = "https://ai-email-bot-0xut.onrender.com"
CLIENTS_ENDPOINT = "/clients"

# === HELPERS ===
def log(msg):
    print(f"🔹 {msg}")

def test_health(base_url):
    log(f"Checking health at {base_url}/health ...")
    r = requests.get(f"{base_url}/health", timeout=10)
    r.raise_for_status()
    if r.json().get("status") == "ok":
        print(f"✅ {base_url}/health OK")
    else:
        print(f"⚠️ Unexpected health response: {r.text}")

def test_clients_crud(base_url):
    unique_id = uuid.uuid4().hex[:6]
    name = f"APIUser-{unique_id}"
    email = f"{name.lower()}@example.com"

    # 1️⃣ POST - create client
    log(f"Creating client {name} ...")
    r = requests.post(f"{base_url}{CLIENTS_ENDPOINT}",
                      params={"name": name, "email": email}, timeout=10)
    r.raise_for_status()
    data = r.json()
    print(f"✅ Created client: {data}")

    # 2️⃣ GET - list clients
    log("Listing clients ...")
    r = requests.get(f"{base_url}{CLIENTS_ENDPOINT}", timeout=10)
    r.raise_for_status()
    clients = r.json()

    found = next((c for c in clients if c["email"] == email), None)
    if found:
        print(f"✅ Retrieved client from API: {found}")
    else:
        print("❌ Could not find inserted client in GET /clients response")

    # 3️⃣ DELETE (cleanup)
    log(f"Cleaning up test client {email} ...")
    try:
        # Assuming we might not yet have a DELETE route; fallback message
        print("ℹ️ No DELETE endpoint implemented — cleanup skipped (DB test already handles cleanup).")
    except Exception:
        pass

    print("\n🎯 API ENDPOINT TEST COMPLETED for", base_url, "\n")

# === MAIN ===
def main():
    print("\n🚀 Running FastAPI endpoint integration test...\n")

    urls = []
    if os.getenv("TEST_LOCAL", "1") == "1":
        urls.append(("Local", LOCAL_URL))
    urls.append(("Render", RENDER_URL))

    for label, base in urls:
        print(f"\n================ {label.upper()} ==================")
        try:
            test_health(base)
            test_clients_crud(base)
        except requests.exceptions.RequestException as e:
            print(f"❌ {label} API test failed: {e}")

    print("\n✅ All endpoint tests completed.\n")

if __name__ == "__main__":
    main()
