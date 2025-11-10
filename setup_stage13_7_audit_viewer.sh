#!/bin/bash
echo "🧮 Setting up THE13TH Stage 13.7 — Audit Log Viewer..."

# 1. Create new HTML template
cat > templates/admin_audit_log.html <<'HTML'
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Admin Audit Log — THE13TH</title>
  <link rel="stylesheet" href="/static/the13th.css">
  <style>
    body { padding: 2rem; }
    table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
    th, td { padding: 0.6rem; border-bottom: 1px solid #444; text-align: left; }
    th { color: #a78bfa; }
    .actions { margin-bottom: 1rem; }
    .btn { background: #6d28d9; color: white; padding: 0.4rem 0.8rem; border-radius: 6px; text-decoration: none; margin-right: 0.5rem; }
    .btn:hover { background: #7c3aed; }
    .back { color: #999; text-decoration: none; }
  </style>
</head>
<body>
  <h1>🔍 Admin Audit Log</h1>
  <div class="actions">
    <a href="/admin/tools" class="btn">← Back to Tools</a>
    <a href="/admin/audit-log?export=1" class="btn">⬇ Export JSON</a>
    <form method="POST" action="/admin/clear-audit" style="display:inline;">
      <button class="btn" style="background:#ef4444;">🗑 Clear Logs</button>
    </form>
  </div>

  {% if logs %}
  <table>
    <tr><th>Timestamp</th><th>Actor</th><th>Event</th></tr>
    {% for entry in logs %}
    <tr>
      <td>{{ entry.ts }}</td>
      <td>{{ entry.actor }}</td>
      <td>{{ entry.event }}</td>
    </tr>
    {% endfor %}
  </table>
  {% else %}
  <p>No audit events found.</p>
  {% endif %}
</body>
</html>
HTML

# 2. Inject FastAPI route into main.py
awk '/# === Admin Tools Routes ===/{print; print "
@app.get(\"/admin/audit-log\", response_class=HTMLResponse)
async def view_audit_log(request: Request, export: bool = False, session_token: str = Depends(auth_admin)):
    log_path = Path(\"logs/admin_audit.log\")
    entries = []
    if log_path.exists():
        with open(log_path) as f:
            for line in f:
                try:
                    entries.append(json.loads(line.strip()))
                except:
                    pass
    if export:
        return JSONResponse(entries)
    return templates.TemplateResponse(\"admin_audit_log.html\", {\"request\": request, \"logs\": entries})

@app.post(\"/admin/clear-audit\")
async def clear_audit_logs(request: Request, session_token: str = Depends(auth_admin)):
    Path(\"logs/admin_audit.log\").write_text(\"\")
    return RedirectResponse(url=\"/admin/audit-log\", status_code=302)
"; next}1' main.py > tmp && mv tmp main.py

# 3. Commit changes
git add main.py templates/admin_audit_log.html
git commit -m "Stage 13.7 — Add Admin Audit Log Viewer dashboard"
git push origin main

echo "✅ Stage 13.7 setup complete!"
echo "➡ Restart with: uvicorn main:app --reload"
echo "➡ Then visit: http://127.0.0.1:8000/admin/audit-log"
