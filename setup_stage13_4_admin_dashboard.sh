#!/bin/bash
echo "🧮 Setting up THE13TH Stage 13.4 — Admin Portal Dashboard..."

mkdir -p templates static/js

# 1️⃣ Admin Dashboard HTML
cat > templates/admin_dashboard.html <<'HTML'
<!doctype html>
<html>
<head>
  <title>THE13TH — Admin Dashboard</title>
  <link rel="stylesheet" href="/static/the13th.css">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    .stats { display: flex; gap: 2em; margin: 1em 0; }
    .stat { background: #1b1b1b; padding: 1em; border-radius: 10px; color: #eee; }
    canvas { background: #101010; border-radius: 8px; padding: 10px; }
  </style>
</head>
<body class="page">
<h1>🧩 THE13TH Admin Dashboard</h1>
<div class="stats">
  <div class="stat">
    <h3>📊 Requests Today</h3>
    <p>{{ metrics.requests_today }}</p>
  </div>
  <div class="stat">
    <h3>⚙️ Avg Response</h3>
    <p>{{ metrics.avg_duration_ms }} ms</p>
  </div>
  <div class="stat">
    <h3>📧 Emails Sent</h3>
    <p>{{ email_stats.sent }}</p>
  </div>
  <div class="stat">
    <h3>❌ Failed Emails</h3>
    <p>{{ email_stats.failed }}</p>
  </div>
</div>

<h2>📈 Activity (Last 24h)</h2>
<canvas id="requestsChart" width="800" height="300"></canvas>

<h2>📜 Recent Email Logs</h2>
<pre style="background:#111;color:#0f0;padding:1em;border-radius:8px;max-height:250px;overflow:auto;">{{ email_log }}</pre>

<footer><a href="/">← Back Home</a></footer>

<script>
const ctx = document.getElementById('requestsChart');
new Chart(ctx, {
  type: 'line',
  data: {
    labels: {{ chart_labels|safe }},
    datasets: [{
      label: 'Requests per Hour',
      data: {{ chart_data|safe }},
      borderColor: '#a855f7',
      borderWidth: 2,
      fill: false,
      tension: 0.3
    }]
  },
  options: {
    scales: { x: { ticks: { color: '#ccc' } }, y: { ticks: { color: '#ccc' } } },
    plugins: { legend: { labels: { color: '#ccc' } } }
  }
});
</script>
</body>
</html>
HTML

# 2️⃣ Add admin dashboard route to main.py
if ! grep -q "/admin/overview" main.py; then
cat >> main.py <<'PYCODE'

# === Stage 13.4: Admin Overview Dashboard ===
@app.get("/admin/overview", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    from utils.telemetry import parse_today_metrics
    from pathlib import Path
    import json, datetime

    metrics = parse_today_metrics()
    log_path = Path("logs/email_delivery.log")
    log_text = log_path.read_text()[-3000:] if log_path.exists() else "No emails logged yet."

    sent = failed = 0
    if log_path.exists():
        for line in log_text.splitlines():
            if "SENT" in line: sent += 1
            elif "FAILED" in line: failed += 1
    email_stats = {"sent": sent, "failed": failed}

    # Generate dummy hourly request data for chart
    now = datetime.datetime.utcnow()
    hours = [(now - datetime.timedelta(hours=i)).strftime("%H:%M") for i in range(12)][::-1]
    data = [max(0, metrics["requests_today"] // 12 + i % 3) for i in range(12)]

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "metrics": metrics,
        "email_stats": email_stats,
        "chart_labels": json.dumps(hours),
        "chart_data": json.dumps(data),
        "email_log": log_text
    })
PYCODE
  echo "🧩 Added /admin/overview dashboard route to main.py"
else
  echo "✅ /admin/overview route already exists."
fi

echo "💾 Committing Stage 13.4 files..."
git add templates/admin_dashboard.html main.py
git commit -m "Add Stage 13.4 Admin Portal Dashboard (v5.0.0)"
git push origin main

echo "🚀 Stage 13.4 setup complete!"
echo "➡ Restart with: uvicorn main:app --reload"
echo "➡ Visit: http://127.0.0.1:8000/admin/overview"
