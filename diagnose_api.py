# diagnose_api.py
"""
Diagnose FastAPI routes (local) and deployed endpoints (Render).

1) Inspects local app routes to confirm /clients is registered.
2) Tests local endpoints using FastAPI TestClient (no uvicorn needed).
3) Tests Render endpoints over HTTPS.
4) Prints clear guidance on fixes.

Run: python diagnose_api.py
"""

import os
import sys
import uuid
from typing import List, Tuple

import requests

# --- 1) Import your local FastAPI app ---
try:
    from app.main import app  # your FastAPI instance
except Exception as e:
    print("❌ Could not import FastAPI app from app.main:app")
    print(f"   Error: {e}")
    sys.exit(1)

# --- 2) Use TestClient for local testing (no server needed) ---
try:
    from fastapi.testclient import TestClient
    local_client = TestClient(app)
except Exception as e:
    print("❌ Could not initialize FastAPI TestClient")
    print(f"   Error: {e}")
    sys.exit(1)

RENDER_BASE = "https://ai-email-bot-0xut.onrender.com"
CLIENTS_PATH = "/clients"
HEALTH_PATH = "/health"


def list_routes() -> List[Tuple[str, List[str]]]:
    """Return list of (path, methods) for all routes in local app."""
    found = []
    for r in app.routes:
        try:
            path = getattr(r, "path", None)
            methods = list(getattr(r, "methods", []) or [])
            if path:
                found.append((path, methods))
        except Exception:
            pass
    return sorted(found, key=lambda x: x[0])


def has_route(path: str, method: str) -> bool:
    method = method.upper()
    for p, methods in list_routes():
        if p == path and method in methods:
            return True
    return False


def print_routes():
    print("🗺️  Local route map:")
    for p, methods in list_routes():
        print(f"   - {p}  [{', '.join(sorted(m for m in methods if m not in {'HEAD', 'OPTIONS'}))}]")
    print("")


def test_local():
    print("\n================ LOCAL TESTS (TestClient) ================")
    print_routes()

    # Check that /clients endpoints exist locally
    missing_bits = []
    if not has_route(CLIENTS_PATH, "GET"):
        missing_bits.append("GET /clients")
    if not has_route(CLIENTS_PATH, "POST"):
        missing_bits.append("POST /clients")

    if missing_bits:
        print("❌ Missing local routes:", ", ".join(missing_bits))
        print("   → Ensure in app/main.py you have something like:")
        print("       from .api import routes_clients")
        print("       app.include_router(routes_clients.router)")
        print("   → And that routes_clients.py defines:")
        print("       router = APIRouter(prefix='/clients', ...)")
        print("   Skipping local CRUD tests due to missing routes.\n")
    else:
        # Health
        r = local_client.get(HEALTH_PATH)
        r.raise_for_status()
        assert r.json().get("status") == "ok"
        print(f"✅ Local {HEALTH_PATH} OK via TestClient")

        # Create and list
        uid = uuid.uuid4().hex[:6]
        name = f"DiagLocal-{uid}"
        email = f"{name.lower()}@example.com"

        r = local_client.post(CLIENTS_PATH, params={"name": name, "email": email})
        r.raise_for_status()
        created = r.json()
        print(f"✅ Local POST {CLIENTS_PATH} created: {created}")

        r = local_client.get(CLIENTS_PATH)
        r.raise_for_status()
        items = r.json()
        found = next((c for c in items if c.get("email") == email), None)
        if found:
            print(f"✅ Local GET {CLIENTS_PATH} retrieved inserted client")
        else:
            print(f"❌ Local GET {CLIENTS_PATH} did not include inserted client")


def test_render():
    print("\n================ RENDER (DEPLOYED) TESTS =================")
    # Health
    try:
        r = requests.get(f"{RENDER_BASE}{HEALTH_PATH}", timeout=10)
        r.raise_for_status()
        if r.json().get("status") == "ok":
            print(f"✅ Render {HEALTH_PATH} OK")
        else:
            print(f"⚠️ Unexpected Render health response: {r.text}")
    except requests.RequestException as e:
        print(f"❌ Render health check failed: {e}")
        return

    # Create and list on Render
    try:
        uid = uuid.uuid4().hex[:6]
        name = f"DiagRender-{uid}"
        email = f"{name.lower()}@example.com"

        r = requests.post(f"{RENDER_BASE}{CLIENTS_PATH}",
                          params={"name": name, "email": email},
                          timeout=10)
        if r.status_code == 404:
            print("❌ Render returned 404 for POST /clients")
            print("   Likely causes:")
            print("   1) Latest code with routes_clients/router is not deployed")
            print("      → Commit & push, then trigger a redeploy on Render.")
            print("   2) app.main does not include the router in the deployed image")
            print("      → Ensure app/main.py has: app.include_router(routes_clients.router)")
            print("   3) Render is starting a different module (old entrypoint)")
            print("      → In render.yaml, startCommand must be: uvicorn app.main:app --host 0.0.0.0 --port 10000")
            print("   4) Different prefix used (e.g., '/api/clients')")
            print("      → Confirm 'prefix=\"/clients\"' in routes_clients.py or adjust test path.")
            return
        r.raise_for_status()
        created = r.json()
        print(f"✅ Render POST {CLIENTS_PATH} created: {created}")

        r = requests.get(f"{RENDER_BASE}{CLIENTS_PATH}", timeout=10)
        r.raise_for_status()
        items = r.json()
        found = next((c for c in items if c.get("email") == created.get("email")), None)
        if found:
            print(f"✅ Render GET {CLIENTS_PATH} retrieved inserted client")
        else:
            print(f"❌ Render GET {CLIENTS_PATH} did not include inserted client")
    except requests.RequestException as e:
        print(f"❌ Render API test failed: {e}")


def main():
    print("\n🚀 Diagnosing FastAPI routes and deployed endpoints...\n")
    test_local()
    test_render()
    print("\n✅ Diagnosis finished.\n")


if __name__ == "__main__":
    main()
