#!/bin/bash
set -e

BASE="frontend"
mkdir -p $BASE

echo "✅ Creating dashboard UI..."

cat << 'HTML' > $BASE/index.html
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8" />
<title>THE13TH — Live Analytics</title>
<style>
  body { font-family: Arial, sans-serif; background:#111; color:#d6d1ff; padding:20px; }
  h1 { color:#c2b6ff; }
  .box { background:#1b1830; padding:12px; border-radius:6px; margin-top:10px; }
  pre { white-space: pre-wrap; }
</style>
</head>
<body>
  <h1>THE13TH — Live Analytics</h1>

  <div class="box"><strong>Scores</strong><pre id="scores">loading...</pre></div>
  <div class="box"><strong>Trend</strong><pre id="trend">loading...</pre></div>
  <div class="box"><strong>Users</strong><pre id="users">loading...</pre></div>
  <div class="box"><strong>Timeseries</strong><pre id="ts">loading...</pre></div>

<script>
  const BASE = "https://the13th.onrender.com";
  async function fetchJSON(url) {
    try { return await (await fetch(url)).json(); }
    catch (e) { return {error: e.message}; }
  }
  async function update(){
    document.getElementById("scores").textContent = JSON.stringify(await fetchJSON(BASE+"/analytics/analytics/scores"), null, 2);
    document.getElementById("trend").textContent  = JSON.stringify(await fetchJSON(BASE+"/analytics/analytics/trend"), null, 2);
    document.getElementById("users").textContent  = JSON.stringify(await fetchJSON(BASE+"/analytics/analytics/users"), null, 2);
    document.getElementById("ts").textContent     = JSON.stringify(await fetchJSON(BASE+"/analytics/analytics/timeseries"), null, 2);
  }
  update();
  setInterval(update, 10000);
</script>
</body>
</html>
HTML

echo "✅ Optional local static server created (only if you want local hosting)..."
cat << 'PY' > $BASE/server.py
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

os.chdir("frontend")
print("Serving dashboard → http://localhost:9000")
HTTPServer(("0.0.0.0", 9000), SimpleHTTPRequestHandler).serve_forever()
PY

chmod +x setup_dashboard.sh

echo -e "\n🎉 Done."
echo "To run dashboard locally (optional):"
echo "  cd frontend && python server.py"
echo "Then open → http://localhost:9000"
echo ""
echo "⚠️ If you get CORS errors, add this in main.py:"
echo '
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
'
