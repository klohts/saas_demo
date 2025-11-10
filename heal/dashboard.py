from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pathlib import Path

router = APIRouter()
LOG_FILE = "uvicorn_fix.log"

@router.get("/heal/logs", response_class=HTMLResponse)
def view_heal_logs():
    data = Path(LOG_FILE).read_text() if Path(LOG_FILE).exists() else "No logs yet"
    data = data.replace("\n", "<br>")
    return f"""
    <html><head><title>THE13TH Logs</title></head>
    <body style='background:#111;color:#0f0;font-family:monospace;padding:20px;'>
    <h2>🧠 THE13TH Auto-Heal Logs</h2>
    <div style='border:1px solid #333;padding:10px;height:70vh;overflow:auto;'>{data}</div>
    </body></html>
    """
