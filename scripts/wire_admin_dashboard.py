import os, re, sys, time

PROFILE_ROOT = os.getcwd()
BACKEND_FILE = "main_admin_intel.py"
APP_FILE = "frontend/src/App.jsx"

print("\n🧠 Wiring THE13TH Admin Dashboard...\n")

# --- 1. Patch BACKEND API endpoints ---
backend_patch = r"""
# ================= ADMIN DASHBOARD API INJECTED =================

from fastapi import Body

# Track socket stats
SOCKET_STATS = {
    "connected_clients": 0,
    "last_message_ts": None,
    "total_sent": 0
}

# Track connected sockets count
@app.websocket("/intel/stream")
async def track_socket(websocket):
    global SOCKET_STATS
    await websocket.accept()
    SOCKET_STATS["connected_clients"] += 1
    try:
        while True:
            data = await websocket.receive_text()
            SOCKET_STATS["last_message_ts"] = datetime.utcnow().isoformat()
            SOCKET_STATS["total_sent"] += 1
            await websocket.send_text(data)
    except:
        pass
    finally:
        SOCKET_STATS["connected_clients"] -= 1

@app.get("/admin/api/socket_stats")
def api_socket_stats():
    return SOCKET_STATS

@app.get("/admin/api/email_queue")
def api_email_queue():
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM email_queue ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]

@app.post("/admin/api/email_queue/{qid}/retry")
def api_email_retry(qid: int):
    with sqlite3.connect(DB_PATH) as db:
        row = db.execute("SELECT * FROM email_queue WHERE id=?", (qid,)).fetchone()
        if not row:
            return {"status":"not_found"}
        enqueue_email(row[1], row[2], row[3], row[4])
        return {"status":"requeued"}

@app.delete("/admin/api/email_queue/{qid}")
def api_email_delete(qid: int):
    with sqlite3.connect(DB_PATH) as db:
        db.execute("DELETE FROM email_queue WHERE id=?", (qid,))
        db.commit()
    return {"status":"deleted"}

@app.get("/admin/api/email_logs")
def api_email_logs(limit: int = 200):
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT * FROM email_logs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

# ==============================================================
"""

if os.path.exists(BACKEND_FILE):
    with open(BACKEND_FILE, "r", encoding="utf-8") as f:
        code = f.read()
    if "ADMIN DASHBOARD API INJECTED" not in code:
        code += backend_patch
        with open(BACKEND_FILE, "w", encoding="utf-8") as f:
            f.write(code)
        print("✅ Backend API endpoints injected into main_admin_intel.py")
    else:
        print("⚠️  Backend API endpoints already exist, skipping")
else:
    print("❌ main_admin_intel.py not found")
    sys.exit(1)

# --- 2. Create/patch App.jsx for routing ---
app_patch = """
import { BrowserRouter, Routes, Route } from "react-router-dom";
import AdminDashboard from "./components/AdminDashboard";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/admin" element={<AdminDashboard />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
"""

os.makedirs(os.path.dirname(APP_FILE), exist_ok=True)
with open(APP_FILE, "w", encoding="utf-8") as f:
    f.write(app_patch)
print("✅ App.jsx routing updated for /admin → AdminDashboard")

# --- 3. Restart services ---
print("\n🔁 Restarting Uvicorn...\n")
os.system("pkill -f uvicorn")
os.system("set -a && source .env && set +a")
os.system("uvicorn main_admin_intel:app --reload &")

print("""
✅ All wired!

Now open in browser:

💻 Dashboard:      http://127.0.0.1:8000/admin
🐝 Email Logs:     http://127.0.0.1:8000/admin/api/email_logs
📦 Email Queue:    http://127.0.0.1:8000/admin/api/email_queue
📊 Socket Stats:   http://127.0.0.1:8000/admin/api/socket_stats

🔥 You are live.
""")
